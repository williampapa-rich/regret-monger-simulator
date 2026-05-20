"""껄무새 시뮬레이터 엔트리포인트."""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from PyQt6 import QtWidgets

# 패키지 import 전에 .env 로드 (KRX_ID 등이 모듈 import 시점에 필요)
load_dotenv(Path(__file__).resolve().parent / ".env")

from regret.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
