#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 下载器主程序
作者: Alex Chen
版本: 1.0.0
描述: 一个简单的YouTube视频、音频和字幕下载工具
"""

import os
import sys
import logging
from modules.gui import YouTubeDownloaderGUI

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("downloader.log"),
        logging.StreamHandler()
    ]
)

def main():
    """主函数 - 创建并运行GUI应用"""
    # 创建应用实例
    app = YouTubeDownloaderGUI()
    # 启动主循环
    app.mainloop()

if __name__ == "__main__":
    main()