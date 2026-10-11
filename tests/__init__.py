#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EasyLink 单元测试包

在包初始化时把仓库根目录加入 sys.path，这样无论从哪个工作目录执行
`python -m unittest discover -s tests -t .` 都能正确导入被测模块。
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
