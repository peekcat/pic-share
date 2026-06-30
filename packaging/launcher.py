"""PyInstaller 入口脚本。

PyInstaller 需要一个可执行的脚本作为分析起点；这里直接调用桌面入口的
``main()``。src 布局下，``picshare`` 包通过 spec 里的 ``pathex=['src']``
（以及构建前的 ``pip install -e .``）可被导入。
"""

from picshare.desktop import main

if __name__ == "__main__":
    main()
