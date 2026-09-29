import math
import unittest

from cholesky import cholesky, generate_spd, relative_residual


class CholeskyTests(unittest.TestCase):
    def test_known_factor_and_input_preserved(self):
        a = [[4.0, 12.0, -16.0], [12.0, 37.0, -43.0], [-16.0, -43.0, 98.0]]
        original = [row[:] for row in a]
        expected = [[2.0, 0.0, 0.0], [6.0, 1.0, 0.0], [-8.0, 5.0, 3.0]]
        self.assertEqual(cholesky(a), expected)
        self.assertEqual(a, original)
        self.assertEqual(relative_residual(a, expected), 0.0)

    def test_scalar_and_identity(self):
        self.assertEqual(cholesky([[9.0]]), [[3.0]])
        identity = [[float(i == j) for j in range(5)] for i in range(5)]
        self.assertEqual(cholesky(identity), identity)

    def test_generated_spd(self):
        for n in (2, 7, 16, 31):
            for seed in (0, 42, 2026):
                with self.subTest(n=n, seed=seed):
                    a = generate_spd(n, seed)
                    lower = cholesky(a)
                    self.assertLess(relative_residual(a, lower), 1e-12)
                    self.assertTrue(all(lower[i][i] > 0 for i in range(n)))

    def test_invalid_inputs(self):
        cases = [[], [[1, 2]], [[1, 2], [0, 1]], [[1, 2], [2, 1]],
                 [[1, 1], [1, 1]], [[-1]], [[math.nan]], [[math.inf]]]
        for a in cases:
            with self.subTest(a=a), self.assertRaises(ValueError):
                cholesky(a)

    def test_residual_detects_wrong_factor(self):
        self.assertGreater(relative_residual([[4.0]], [[1.0]]), 0.1)


if __name__ == "__main__":
    unittest.main()
