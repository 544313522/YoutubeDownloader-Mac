#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yt_dlp
import logging
from typing import Dict, Any, Optional, Callable

class YouTubeDownloader:
    """YouTube 下载器，封装 yt-dlp 库功能"""
    
    def __init__(self, default_save_path: str = '~/Downloads'):
        """
        初始化下载器
        
        Args:
            default_save_path: 默认保存路径
        """
        self.default_save_path = os.path.expanduser(default_save_path)
        self.current_download = None
        self.logger = logging.getLogger(__name__) 
    
    def _get_save_path(self, save_path: Optional[str] = None) -> str:
        """获取保存路径，如未指定则使用默认路径"""
        if save_path:
            return os.path.expanduser(save_path)
        return self.default_save_path
    
    def _progress_hook(self, progress_callback: Optional[Callable] = None):
        """创建下载进度回调函数"""
        def hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                else:
                    percent = 0
                
                if progress_callback:
                    progress_callback(percent, d.get('_speed_str', ''), d.get('_eta_str', ''))
            
            elif d['status'] == 'finished':
                if progress_callback:
                    progress_callback(100, '完成', '0s')
                self.logger.info(f"下载完成: {d['filename']}")
                
            elif d['status'] == 'error':
                self.logger.error(f"下载错误: {d.get('error', '未知错误')}")
        
        return hook
    
    def download_video(self, url: str, resolution: str = 'best', save_path: str = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        下载视频
        
        Args:
            url: 视频链接
            resolution: 分辨率（best / 720p / 1080p）
            save_path: 保存目录
            progress_callback: 进度回调函数，接收参数(percent, speed, eta)
            
        Returns:
            包含下载信息的字典
        """
        save_path = self._get_save_path(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        if resolution != 'best':
            if resolution == '720p':
                format_spec = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
            elif resolution == '1080p':
                format_spec = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best'
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook(progress_callback)],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return {
                    'title': info.get('title', '未知标题'),
                    'filename': ydl.prepare_filename(info),
                    'duration': info.get('duration'),
                    'resolution': info.get('resolution', resolution),
                    'success': True
                }
        except Exception as e:
            self.logger.error(f"视频下载失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_audio(self, url: str, audio_format: str = 'mp3', save_path: str = None,
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        下载音频
        
        Args:
            url: 视频链接
            audio_format: mp3 / m4a
            save_path: 保存目录
            progress_callback: 进度回调函数，接收参数(percent, speed, eta)
            
        Returns:
            包含下载信息的字典
        """
        save_path = self._get_save_path(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook(progress_callback)],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # 修正文件扩展名为实际的音频格式
                filename = os.path.splitext(filename)[0] + f".{audio_format}"
                return {
                    'title': info.get('title', '未知标题'),
                    'filename': filename,
                    'duration': info.get('duration'),
                    'format': audio_format,
                    'success': True
                }
        except Exception as e:
            self.logger.error(f"音频下载失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_subtitles(self, url: str, language: str = 'en', save_path: str = None,
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        下载字幕
        
        Args:
            url: 视频链接
            language: 字幕语言代码 (en, zh-CN, ja, ko, etc.)
            save_path: 保存目录
            progress_callback: 进度回调函数，接收参数(percent, speed, eta)
            
        Returns:
            包含下载信息的字典
        """
        save_path = self._get_save_path(save_path)
        os.makedirs(save_path, exist_ok=True)
        
        ydl_opts = {
            'skip_download': True,  # 不下载视频
            'writesubtitles': True,
            'writeautomaticsub': True,  # 如果没有字幕，尝试自动生成
            'subtitleslangs': [language],
            'subtitlesformat': 'srt',
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook(progress_callback)],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename_base = os.path.splitext(ydl.prepare_filename(info))[0]
                subtitle_filename = f"{filename_base}.{language}.srt"
                
                return {
                    'title': info.get('title', '未知标题'),
                    'filename': subtitle_filename,
                    'language': language,
                    'success': True
                }
        except Exception as e:
            self.logger.error(f"字幕下载失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def cancel_download(self):
        """取消当前下载任务"""
        # yt-dlp 不直接支持取消，这里提供一个接口以便未来扩展
        self.logger.info("尝试取消下载")
        # 实际取消逻辑需要在具体实现中处理
        return True


class Downloader:
    """YouTube 下载器，封装 yt-dlp 库功能"""
    
    def __init__(self, default_save_path: str = '~/Downloads'):
        # 默认下载路径
        self.default_save_path = os.path.expanduser(default_save_path)

    def _progress_hook(self, d):
        """
        下载进度钩子（预留给 GUI 队列）
        """
        if d['status'] == 'downloading':
            print(f"[下载中] {d.get('_percent_str', '')} {d.get('_eta_str', '')}")
        if d['status'] == 'finished':
            print(f"[完成] 文件已保存：{d['filename']}")

    def download_video(self, url: str, resolution: str = 'best', save_path: str = None):
        """
        下载视频
        - url: 视频链接
        - resolution: 分辨率（best / 720p / 1080p）
        - save_path: 保存目录
        """
        save_path = save_path or self.default_save_path
        output_template = os.path.join(save_path, '%(title)s.%(ext)s')

        # yt-dlp 下载选项
        ydl_opts = {
            'outtmpl': output_template,
            'format': f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]' if resolution != 'best' else 'best',
            'noplaylist': False,
            'merge_output_format': 'mp4',
            'progress_hooks': [self._progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[下载视频出错] {e}")

    def download_audio(self, url: str, audio_format: str = 'mp3', save_path: str = None):
        """
        下载音频
        - url: 视频链接
        - audio_format: mp3 / m4a
        - save_path: 保存目录
        """
        save_path = save_path or self.default_save_path
        output_template = os.path.join(save_path, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': audio_format,
            'noplaylist': False,
            'progress_hooks': [self._progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[下载音频出错] {e}")

    def download_subtitles(self, url: str, language: str = 'en', save_path: str = None):
        """
        下载字幕
        - url: 视频链接
        - language: 字幕语言
        - save_path: 保存目录
        """
        save_path = save_path or self.default_save_path
        output_template = os.path.join(save_path, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language],
            'skip_download': True,
            'progress_hooks': [self._progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[下载字幕出错] {e}")