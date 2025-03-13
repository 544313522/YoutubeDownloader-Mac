#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from modules.downloader import YouTubeDownloader

def progress_callback(percent, speed, eta):
    """简单的进度回调函数"""
    print(f"下载进度: {percent:.1f}% | 速度: {speed} | 剩余时间: {eta}")

def main():
    # 创建下载目录
    download_dir = os.path.expanduser("~/Downloads/youtube_test")
    os.makedirs(download_dir, exist_ok=True)
    
    # 初始化下载器
    downloader = YouTubeDownloader(default_save_path=download_dir)
    
    # 要下载的视频URL
    video_url = "https://www.youtube.com/watch?v=9Shl1-ZJI6E"
    
    print("=== 开始下载视频 ===")
    result = downloader.download_video(
        url=video_url,
        resolution="720p",  # 可选: 'best', '720p', '1080p'
        progress_callback=progress_callback
    )
    print(f"视频下载结果: {result}")
    
    print("\n=== 开始下载音频 ===")
    result = downloader.download_audio(
        url=video_url,
        audio_format="mp3",  # 可选: 'mp3', 'm4a'
        progress_callback=progress_callback
    )
    print(f"音频下载结果: {result}")
    
    print("\n=== 开始下载字幕 ===")
    result = downloader.download_subtitles(
        url=video_url,
        language="zh-CN",  # 中文字幕，可选: 'en', 'zh-CN', 'ja', 等
        progress_callback=progress_callback
    )
    print(f"字幕下载结果: {result}")
    
    print(f"\n所有文件已下载到: {download_dir}")

if __name__ == "__main__":
    main()