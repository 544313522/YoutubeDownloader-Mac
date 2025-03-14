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
        # 移除 self.current_download
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
    
    # 修复 _progress_hook 参数问题
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
            'progress_hooks': [self._progress_hook(progress_callback)],  # 修正这里
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
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback)],  # 修改这里
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
    
    def download_subtitles(self, url: str, language: str = 'zh-CN', save_path: Optional[str] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        try:
            save_path = self._get_save_path(save_path)
            os.makedirs(save_path, exist_ok=True)  # 确保目录存在
            
            # 先获取视频信息，检查可用的字幕
            info_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # 只提取元数据，不下载视频
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 获取所有可用的字幕语言
                available_subs = set()
                if 'subtitles' in info:
                    available_subs.update(info['subtitles'].keys())
                if 'automatic_captions' in info:
                    available_subs.update(info['automatic_captions'].keys())
                
                print(f"可用的字幕语言: {available_subs}")  # 调试信息
                
                # 检查中文字幕的各种可能的语言代码
                chinese_codes = ['zh', 'zh-CN', 'zh-Hans', 'zh-Hant', 'zh-TW']
                target_language = None
                
                # 如果请求的是中文字幕，检查所有可能的中文代码
                if language.startswith('zh'):
                    for code in chinese_codes:
                        if code in available_subs:
                            target_language = code
                            break
                else:
                    # 非中文字幕直接检查
                    if language in available_subs:
                        target_language = language
                
                # 如果没找到目标语言但有英文字幕，使用英文
                if not target_language and 'en' in available_subs:
                    target_language = 'en'
                
                if not target_language:
                    return {
                        'success': False,
                        'error': f'该视频既没有{language}语言的字幕，也没有英文字幕'
                    }
                
                # 设置下载选项
                ydl_opts = {
                    'skip_download': True,  # 确保不下载视频
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': [target_language],
                    'subtitlesformat': 'vtt',
                    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),  # 确保使用正确的保存路径
                    'quiet': True,
                    'no_warnings': True,
                }
                
                # 下载字幕
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # 检查下载的文件
                for filename in os.listdir(save_path):
                    if filename.endswith(f'.{target_language}.vtt'):
                        subtitle_type = 'auto' if target_language in info.get('automatic_captions', {}) else 'manual'
                        return {
                            'success': True,
                            'title': info.get('title', '未知标题'),
                            'filename': filename,
                            'subtitle_type': subtitle_type,
                            'language': target_language
                        }
                
                return {
                    'success': False,
                    'error': '字幕下载失败'
                }
                
        except Exception as e:
            print(f"字幕下载出错: {str(e)}")  # 添加错误输出
            return {
                'success': False,
                'error': str(e)
            }    
    def _progress_hook(self, d: Dict[str, Any], callback: Optional[Callable] = None):
        """处理下载进度回调"""
        if callback and 'downloaded_bytes' in d:
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total_bytes > 0:
                percent = (d['downloaded_bytes'] / total_bytes) * 100
            else:
                percent = 0
                
            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed/1024/1024:.1f} MB/s"
            else:
                speed_str = "未知"
                
            eta = d.get('eta', 0)
            if eta:
                eta_str = f"{eta}秒"
            else:
                eta_str = "未知"
                
            callback(percent, speed_str, eta_str)


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
