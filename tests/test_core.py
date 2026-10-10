import os
import random
import tempfile
import unittest
import xml.dom.minidom

from cxltier import decision_matrix, linux_backend
from cxltier.config import SimConfig, TierSpec
from cxltier.experiments import run_matrix, summarize, write_csv
from cxltier.hotness import HotnessEstimator
from cxltier.journal import Journal, JournalError, replay
from cxltier.monitor import AccessMonitor
from cxltier.plotting import grouped_bar_svg, line_svg
from cxltier.policies import POLICY_NAMES, make_policy
from cxltier.simulator import SimulatedCrash, Simulator
from cxltier.stats import mean_std_ci, weighted_percentile
from cxltier.workloads import WORKLOADS, generate

SMALL = dict(num_pages=512, epochs=12, accesses_per_epoch=3000)


def small_cfg(**kw):
    d = dict(SMALL)
    d.update(kw)
    return SimConfig(**d)


class ConfigTests(unittest.TestCase):
    def test_defaults_valid(self):
        c = SimConfig()
        self.assertEqual(len(c.tiers), 3)
        self.assertTrue(c.tiers[2].persistent and c.tiers[2].emulated)

    def test_rejects_bad_values(self):
        with self.assertRaises(ValueError):
            SimConfig(monitor_sample_rate=0.0)
        with self.assertRaises(ValueError):
            SimConfig(stall_fraction=1.5)
        with self.assertRaises(ValueError):
            SimConfig(num_pages=4096, tiers=[TierSpec("a", 10, 1, 1, 1), TierSpec("b", 10, 1, 1, 1)])

    def test_json_roundtrip_and_replace(self):
        c = SimConfig()
        c2 = SimConfig.from_dict(c.to_dict())
        self.assertEqual(c2.tiers, c.tiers)
        c3 = c.replace(num_pages=1024)
        self.assertEqual(c3.tiers[0].capacity_pages, 128)
        self.assertEqual(c.replace(stall_fraction=1.0).stall_fraction, 1.0)

    def test_copy_cost_uses_slower_bandwidth_and_extra(self):
        c = SimConfig()
        self.assertAlmostEqual(c.copy_ns(0, 1), 3000 + 4096 / 8.0)
        self.assertAlmostEqual(c.copy_ns(1, 2), 3000 + 4096 / 2.0 + 2000)


class WorkloadTests(unittest.TestCase):
    def test_all_workloads_exact_totals_and_deterministic(self):
        for w in WORKLOADS:
            a = generate(w, 512, 4, 2000, seed=3)
            b = generate(w, 512, 4, 2000, seed=3)
            c = generate(w, 512, 4, 2000, seed=4)
            self.assertTrue(all(e.total() == 2000 for e in a.epochs), w)
            self.assertEqual([e.reads for e in a.epochs], [e.reads for e in b.epochs], w)
            self.assertNotEqual([e.reads for e in a.epochs], [e.reads for e in c.epochs], w)
            self.assertTrue(all(0 <= p < 512 for e in a.epochs for p in list(e.reads) + list(e.writes)))

    def test_unknown_workload(self):
        with self.assertRaises(KeyError):
            generate("nope", 512, 2, 100)

    def test_phase_changes_hot_set(self):
        t = generate("phase", 1024, 20, 5000, 0)
        top = lambda e: set(sorted(range(1024), key=lambda p: -t.epochs[e].page_total(p))[:50])
        self.assertLess(len(top(2) & top(15)), 15)
        self.assertGreater(len(top(2) & top(3)), 25)


class MonitorHotnessTests(unittest.TestCase):
    def test_exact_when_rate_one(self):
        m = AccessMonitor(1.0, random.Random(1))
        r, w, s = m.observe({1: 5, 2: 7}, {1: 2})
        self.assertEqual((r, w, s), ({1: 5.0, 2: 7.0}, {1: 2.0}, 14))

    def test_sampling_is_roughly_unbiased(self):
        m = AccessMonitor(0.1, random.Random(2))
        tot = sum(sum(m.observe({0: 1000}, {})[0].values()) for _ in range(200)) / 200
        self.assertAlmostEqual(tot, 1000, delta=40)

    def test_bad_rate(self):
        with self.assertRaises(ValueError):
            AccessMonitor(1.5, random.Random(0))

    def test_normalization_across_epoch_lengths(self):
        a = HotnessEstimator(100, 1000)
        b = HotnessEstimator(100, 10000)
        for e in range(6):
            a.update(e, {7: 100.0}, {})
            b.update(e, {7: 1000.0}, {})
        self.assertAlmostEqual(a.heat_rel(7), b.heat_rel(7))

    def test_recency_factor_bounds_and_decay(self):
        h = HotnessEstimator(10, 100, w_recency=0.5, tau=2.0)
        h.update(0, {1: 10.0}, {})
        self.assertAlmostEqual(h.recency_factor(1, 0), 1.0)
        self.assertLess(h.recency_factor(1, 5), h.recency_factor(1, 1))
        self.assertGreaterEqual(h.recency_factor(1, 1000), 0.5 - 1e-9)
        self.assertAlmostEqual(h.recency_factor(3, 0), 0.5, places=3)  # never touched


class SimulatorInvariantTests(unittest.TestCase):
    def check_state(self, sim):
        T = len(sim.cfg.tiers)
        occ = [0] * T
        for t in sim.tier_of:
            self.assertTrue(0 <= t < T)
            occ[t] += 1
        self.assertEqual(occ, sim.occ)
        for t in range(T):
            self.assertLessEqual(occ[t], sim.cfg.tiers[t].capacity_pages)

    def test_every_policy_keeps_invariants(self):
        cfg = small_cfg(migration_fail_prob=0.05)
        for w in ("zipf", "phase", "uniform"):
            tr = generate(w, cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 1)
            for pn in POLICY_NAMES:
                sim = Simulator(cfg, tr, make_policy(pn), seed=1)
                r = sim.run()
                self.check_state(sim)
                self.assertEqual(r.accesses, cfg.epochs * cfg.accesses_per_epoch, (w, pn))
                self.assertAlmostEqual(r.total_ns, r.access_ns + r.migration_ns + r.overhead_ns, places=3)
                self.assertAlmostEqual(sum(r.tier_access_share), 1.0, places=6)
                self.assertEqual(sum(r.final_occupancy), cfg.num_pages)
                self.assertLessEqual(r.p50_latency_ns, r.p99_latency_ns)

    def test_static_policies_never_migrate_or_monitor(self):
        cfg = small_cfg()
        tr = generate("hotset", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        for pn in ("static_firsttouch", "static_interleave", "oracle_static"):
            r = Simulator(cfg, tr, make_policy(pn), seed=0).run()
            self.assertEqual((r.copies, r.overhead_ns, r.migration_ns), (0, 0.0, 0.0))

    def test_deterministic(self):
        cfg = small_cfg()
        tr = generate("zipf", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 5)
        a = Simulator(cfg, tr, make_policy("adaptive_full"), seed=5).run()
        b = Simulator(cfg, tr, make_policy("adaptive_full"), seed=5).run()
        self.assertEqual(a.total_ns, b.total_ns)
        self.assertEqual(a.copies, b.copies)

    def test_headroom_respected_by_dynamic_policies(self):
        cfg = small_cfg()
        tr = generate("hotset", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        sim = Simulator(cfg, tr, make_policy("freq_only"), seed=0)
        sim.run()
        hr = cfg.headroom()
        for t in (0, 1):
            self.assertGreaterEqual(cfg.tiers[t].capacity_pages - sim.occ[t], hr[t] - 1)

    def test_pinned_pages_never_move_and_failures_counted(self):
        cfg = small_cfg(pinned_fraction=0.2)
        tr = generate("hotset", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        sim = Simulator(cfg, tr, make_policy("freq_only"), seed=0)
        start = list(sim.tier_of)
        r = sim.run()
        for p in sim.pinned:
            self.assertEqual(sim.tier_of[p], start[p])
        self.assertGreater(r.failed_ops, 0)

    def test_hotset_benefit_and_uniform_cost(self):
        cfg = small_cfg()
        hot = generate("hotset", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        base = Simulator(cfg, hot, make_policy("static_firsttouch"), 0).run().total_ns
        dyn = Simulator(cfg, hot, make_policy("freq_cost_conf"), 0).run().total_ns
        self.assertLess(dyn, base)
        uni = generate("uniform", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        m_only = Simulator(cfg, uni, make_policy("freq_only"), 0).run()
        m_conf = Simulator(cfg, uni, make_policy("freq_cost_conf"), 0).run()
        self.assertLess(m_conf.copies, m_only.copies)

    def test_oracle_epoch_is_a_bound(self):
        cfg = small_cfg()
        tr = generate("phase", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        orc = Simulator(cfg, tr, make_policy("oracle_epoch"), 0).run().access_ns
        for pn in ("static_firsttouch", "freq_only", "adaptive_full"):
            self.assertLessEqual(orc, Simulator(cfg, tr, make_policy(pn), 0).run().access_ns)

    def test_config_trace_mismatch(self):
        tr = generate("zipf", 256, 2, 500, 0)
        with self.assertRaises(ValueError):
            Simulator(small_cfg(), tr, make_policy("static_firsttouch"))


class JournalTests(unittest.TestCase):
    def test_replay_commit_and_rollback(self):
        j = Journal()
        g1 = j.begin([(0, 0, 1)])
        j.commit(g1)
        j.begin([(1, 0, 2)])  # never committed
        mapping, rolled = replay([0, 0, 0], j.records)
        self.assertEqual(mapping, [1, 0, 0])
        self.assertEqual(rolled, [2])

    def test_replay_detects_inconsistency(self):
        j = Journal()
        j.commit(j.begin([(0, 1, 2)]))
        with self.assertRaises(JournalError):
            replay([0], j.records)
        with self.assertRaises(JournalError):
            replay([0], [{"op": "COMMIT", "gid": 9}])

    def test_file_journal_and_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "j.log")
            j = Journal(path)
            j.commit(j.begin([(0, 0, 1)]))
            j.close()
            with open(path, "a") as fh:
                fh.write('{"op":"BEGIN","gid":2,"cop')  # torn write
            recs = Journal.load(path)
            self.assertEqual(len(recs), 2)
            with open(path, "a") as fh:
                fh.write('\n{"op":"COMMIT","gid":1}\n')
            with self.assertRaises(JournalError):
                Journal.load(path)

    def test_crash_recovery_matches_live_state(self):
        cfg = small_cfg()
        tr = generate("hotset", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        crashed = 0
        for k in (1, 5, 40):
            j = Journal()
            sim = Simulator(cfg, tr, make_policy("freq_only"), 0, journal=j, journal_scope="all", crash_after_groups=k)
            with self.assertRaises(SimulatedCrash):
                sim.run()
            mapping, rolled = replay(sim.snapshot, j.records)
            self.assertEqual(mapping, sim.tier_of)
            self.assertEqual(len(rolled), 1)
            crashed += 1
        self.assertEqual(crashed, 3)

    def test_clean_run_journal_all_committed(self):
        cfg = small_cfg()
        tr = generate("zipf", cfg.num_pages, cfg.epochs, cfg.accesses_per_epoch, 0)
        j = Journal()
        sim = Simulator(cfg, tr, make_policy("adaptive_full"), 0, journal=j)
        sim.run()
        persistent_snapshot_scope = [r for r in j.records if r["op"] == "BEGIN"]
        commits = [r for r in j.records if r["op"] == "COMMIT"]
        self.assertEqual(len(persistent_snapshot_scope), len(commits))


class StatsPlotReportTests(unittest.TestCase):
    def test_stats(self):
        m, sd, ci = mean_std_ci([1.0, 2.0, 3.0])
        self.assertAlmostEqual(m, 2.0)
        self.assertAlmostEqual(sd, 1.0)
        self.assertAlmostEqual(ci, 4.303 / 3 ** 0.5, places=3)
        self.assertEqual(mean_std_ci([5.0]), (5.0, 0.0, 0.0))
        self.assertEqual(weighted_percentile([(1, 99), (100, 1)], 99), 1)
        self.assertEqual(weighted_percentile([(1, 98), (100, 2)], 99), 100)

    def test_svg_wellformed(self):
        s = grouped_bar_svg("t & <x>", ["a", "b"], {"p1": [1.0, 2.0], "p2": [0.5, float("nan")]})
        xml.dom.minidom.parseString(s)
        xml.dom.minidom.parseString(line_svg("t", {"a": [1, 2, 3], "b": [3, 2, 1]}, "y"))
        with self.assertRaises(ValueError):
            grouped_bar_svg("t", [], {})

    def test_matrix_and_summary_and_csv(self):
        decision_matrix.validate()
        self.assertEqual(sum(w for _, w in decision_matrix.CRITERIA), 100)
        self.assertIn("C", decision_matrix.winner())
        cfg = small_cfg()
        res = run_matrix(cfg, ["zipf"], ["static_firsttouch", "freq_only"], [0, 1])
        s = summarize(res)
        self.assertAlmostEqual(s["zipf"]["static_firsttouch"]["speedup"], 1.0)
        with tempfile.TemporaryDirectory() as d:
            write_csv(res, os.path.join(d, "a", "r.csv"))
            self.assertTrue(os.path.exists(os.path.join(d, "a", "r.csv")))


class LinuxBackendTests(unittest.TestCase):
    def test_probe_does_not_crash(self):
        p = linux_backend.probe()
        self.assertIn("numa_nodes", p)

    def test_dry_run_and_validation(self):
        m = linux_backend.LinuxMigrator(dry_run=True)
        self.assertEqual(m.move(1, [4096, 8192], [0, 1]), [0, 1])
        self.assertEqual(m.move(1, [], []), [])
        with self.assertRaises(ValueError):
            m.move(1, [1], [])
        with self.assertRaises(linux_backend.MigrationError):
            m.query_nodes(1, [1])

    def test_discover_missing_paths(self):
        self.assertEqual(linux_backend.discover_numa_nodes("/nonexistent"), [])
        self.assertEqual(linux_backend.discover_memory_tiers("/nonexistent"), {})


if __name__ == "__main__":
    unittest.main()
