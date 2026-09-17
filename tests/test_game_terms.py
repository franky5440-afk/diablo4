import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import game_in_title


def test_game_in_title_variants():
    assert game_in_title("暗黑破壞神4 賽季攻略")
    assert game_in_title("Diablo IV build guide")
    assert game_in_title("D4 BD 分享")
    assert not game_in_title("Path of Exile 2 build")
