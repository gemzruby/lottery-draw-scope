import unittest
from unittest.mock import patch
from main import *
class Tests(unittest.TestCase):
    def test_chacha8_zero_key_vector(self):
        r=ChaCha8(0); r.key=[0]*8
        self.assertEqual(r.block()[:4],[0x2fef003e,0xd6405f89,0xe8b85b7f,0xa1a5091f])
    def test_seed_expansion(self):
        self.assertEqual(ChaCha8(0).key[0],0xf973f2ec)
    def test_reproducibility(self):
        d=[Draw(1,(1,2,3,4,5,6))]
        a=predict(d,'645',42,10)
        self.assertEqual(a,predict(d,'645',42,10))
        self.assertEqual(len({tuple(x['numbers']) for x in a}),10)
        for t in a:
            self.assertEqual(t['numbers'],sorted(set(t['numbers'])))
            self.assertEqual(len(t['numbers']),6)
    def test_other_products(self):
        for p in ['535','655']:
            a=predict([],p,123,3)
            k=PRODUCTS[p][1]
            for t in a:
                self.assertEqual(len(set(t['numbers'][:k])),k)
                self.assertTrue(1<=t['numbers'][-1]<=PRODUCTS[p][2])
    def test_bonus_pool(self):
        self.assertTrue(all(t['numbers'][-1]==7 for t in predict([],'535',10,5,[7])))
    def test_no_future_leakage(self):
        d=[Draw(i,tuple(range(1,7))) for i in range(1,10)]
        a=backtest(d,'645',3)['rows']
        b=backtest(d+[Draw(10,(30,31,32,33,34,35))],'645',3)['rows']
        self.assertEqual(a,b[:len(a)])
    def test_empty_ticket_request(self): self.assertEqual(predict([],'645',1,0),[])

    def test_mixed_reads_cross_refill(self):
        # Word 63 remains the low half when a u64 read crosses a refill.
        for seed in [0, 42, MASK64]:
            reference = ChaCha8(seed)
            words = [reference.u32() for _ in range(192)]
            r = ChaCha8(seed)
            self.assertEqual([r.u32() for _ in range(63)], words[:63])
            self.assertEqual(r.u64(), words[63] | (words[64] << 32))
            self.assertEqual(r.u32(), words[65])
            for i in range(66, 192, 2):
                self.assertEqual(r.u64(), words[i] | (words[i+1] << 32))
            self.assertEqual(r.counter, 12)

    def test_seed_wraps_modulo_u64(self):
        for seed in [0, 42, MASK64]:
            a, b = ChaCha8(seed), ChaCha8(seed + (1 << 64))
            self.assertEqual(a.key, b.key)
            self.assertEqual([a.u64() for _ in range(70)],
                             [b.u64() for _ in range(70)])
        self.assertEqual(ChaCha8(-1).key, ChaCha8(MASK64).key)

    def test_uniform64_rejection_and_inclusive_zone(self):
        # n=3: zone=3*2**62-1. Its inverse modulo 2**64 gives
        # a draw whose product low half equals zone exactly.
        zone = (3 << 62) - 1
        boundary = (zone * pow(3, -1, 1 << 64)) & MASK64
        r = ChaCha8(0)
        with patch.object(r, 'u64', side_effect=[MASK64, boundary]) as read:
            self.assertEqual(r.below64(3), (boundary * 3) >> 64)
            self.assertEqual(read.call_count, 2)

    def test_uniform32_rejection_and_inclusive_zone(self):
        zone = (~(((1 << 32) - 3) % 3)) & MASK32
        boundary = (zone * pow(3, -1, 1 << 32)) & MASK32
        r = ChaCha8(0)
        with patch.object(r, 'u32', side_effect=[boundary]) as read:
            self.assertEqual(r.below32(3), (boundary * 3) >> 32)
            self.assertEqual(read.call_count, 1)
        rejected = (MASK32 * pow(3, -1, 1 << 32)) & MASK32
        with patch.object(r, 'u32', side_effect=[rejected, 0]) as read:
            self.assertEqual(r.below32(3), 0)
            self.assertEqual(read.call_count, 2)

    def test_duplicate_main_and_complete_ticket_attempt_limit(self):
        # One duplicate number per attempt, then the same complete ticket.
        with patch.object(ChaCha8, 'below64', side_effect=[0,0,1,2,3,4,5]*500) as read:
            self.assertEqual(predict([], '645', 0, 2),
                             [{'numbers': [1,2,3,4,5,6], 'label': 'heuristic-only'}])
            self.assertEqual(read.call_count, 3500)

    def test_bonus_preserves_pool_positions_and_main_overlap(self):
        # Choose index 1: sorting or deduplicating this pool would change it.
        with patch.object(ChaCha8, 'below64', side_effect=[0,1,2,3,4,1]):
            self.assertEqual(predict([], '535', 0, 1, [9,2,2])[0]['numbers'],
                             [1,2,3,4,5,2])

if __name__=='__main__': unittest.main()
