"""DAG 纯图算法单元测试：find_cycle（E-DAG-CYCLE 的判定基础）与 depth_of（D7）。"""

from fractal_kernel.dag import depth_of, find_cycle


class TestFindCycle:
    def test_acyclic_chain(self) -> None:
        assert find_cycle({"a": ("b",), "b": ("c",), "c": ()}) is None

    def test_two_node_cycle(self) -> None:
        assert find_cycle({"a": ("b",), "b": ("a",)}) is not None

    def test_self_loop(self) -> None:
        assert find_cycle({"a": ("a",)}) == ("a", "a")

    def test_three_node_cycle(self) -> None:
        assert find_cycle({"a": ("b",), "b": ("c",), "c": ("a",)}) is not None

    def test_diamond_is_acyclic(self) -> None:
        assert find_cycle({"a": ("b", "c"), "b": ("d",), "c": ("d",), "d": ()}) is None

    def test_dangling_dep_treated_as_leaf(self) -> None:
        assert find_cycle({"a": ("ghost",)}) is None


class TestDepth:
    def test_root_depth_zero(self) -> None:
        assert depth_of("r", {"r": None}) == 0

    def test_grandchild_depth_two(self) -> None:
        parents = {"r": None, "c": "r", "g": "c"}
        assert depth_of("g", parents) == 2
