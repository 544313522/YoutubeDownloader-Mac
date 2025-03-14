#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import threading
import queue
import time
import json
import customtkinter as ctk
from typing import Dict, List, Any, Optional, Tuple
from .downloader import YouTubeDownloader

# 设置外观模式和默认颜色主题
ctk.set_appearance_mode("System")  # 系统、暗色、亮色
ctk.set_default_color_theme("blue")  # 蓝色、绿色、暗蓝色

class DownloadTask:
    """下载任务类，用于管理单个下载任务"""
    
    def __init__(self, url: str, task_type: str = 'video', 
                 options: Dict[str, Any] = None, save_path: str = None):
        """初始化下载任务"""
        self.url = url
        self.task_type = task_type
        self.options = options or {}
        self.save_path = save_path
        self.id = f"{int(time.time())}-{id(self)}"
        self.status = "等待中"  # 等待中、下载中、已完成、已暂停、已取消、失败
        self.progress = 0
        self.speed = ""
        self.eta = ""
        self.title = "获取中..."
        self.filename = ""
        self.thread = None
        self.result = None
    
    def update_progress(self, percent: float, speed: str, eta: str):
        """更新下载进度"""
        self.progress = percent
        self.speed = speed
        self.eta = eta
        if percent < 100:
            self.status = "下载中"
        else:
            self.status = "已完成"
    
    def cancel(self):
        """取消任务"""
        self.status = "已取消"
        return True


class DownloadManager:
    """下载管理器，管理下载队列和任务执行"""
    
    def __init__(self, default_save_path: str = '~/Downloads'):
        """初始化下载管理器"""
        self.downloader = YouTubeDownloader(default_save_path)
        self.tasks: Dict[str, DownloadTask] = {}  # 任务ID -> 任务对象
        self.task_queue = queue.Queue()  # 任务队列
        self.max_concurrent = 2  # 最大并发下载数
        self.running = False
        self.worker_thread = None
        self.url_history = {}  # 新增：URL历史记录，格式为 {url: task_id}
    
    def add_task(self, task: DownloadTask) -> str:
        """添加下载任务到队列"""
        self.tasks[task.id] = task
        self.task_queue.put(task.id)
        
        # 记录URL历史
        self.url_history[task.url] = task.id
        
        # 如果工作线程未运行，启动它
        if not self.running:
            self.start_worker()
        
        return task.id
    
    def start_worker(self):
        """启动工作线程处理下载队列"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
    
    def _process_queue(self):
        """处理下载队列的工作线程"""
        active_tasks = []
        
        while self.running:
            # 检查是否可以启动新任务
            while len(active_tasks) < self.max_concurrent and not self.task_queue.empty():
                try:
                    task_id = self.task_queue.get_nowait()
                    task = self.tasks.get(task_id)
                    if task and task.status == "等待中":
                        self._start_task(task)
                        active_tasks.append(task_id)
                except queue.Empty:
                    break
            
            # 清理已完成的任务
            active_tasks = [t for t in active_tasks if self.tasks.get(t) and 
                           self.tasks[t].status not in ["已完成", "已取消", "失败"]]
            
            # 如果没有活动任务且队列为空，可以退出
            if not active_tasks and self.task_queue.empty():
                break
                
            time.sleep(0.5)
        
        self.running = False
    
    def _start_task(self, task: DownloadTask):
        """启动单个下载任务"""
        task.status = "下载中"
        
        # 创建任务线程
        task.thread = threading.Thread(
            target=self._download_task,
            args=(task,),
            daemon=True
        )
        task.thread.start()
    
    def _download_task(self, task: DownloadTask):
        """执行下载任务的线程函数"""
        try:
            if task.status == "已取消":
                return
                
            if task.task_type == 'video':
                result = self.downloader.download_video(
                    url=task.url,
                    resolution=task.options.get('resolution', 'best'),
                    save_path=task.save_path,
                    progress_callback=lambda p, s, e: task.update_progress(p, s, e)
                )
            elif task.task_type == 'audio':
                result = self.downloader.download_audio(
                    url=task.url,
                    audio_format=task.options.get('format', 'mp3'),
                    save_path=task.save_path,
                    progress_callback=lambda p, s, e: task.update_progress(p, s, e)
                )
            elif task.task_type == 'subtitle':
                result = self.downloader.download_subtitles(
                    url=task.url,
                    language=task.options.get('language', 'en'),
                    save_path=task.save_path,
                    progress_callback=lambda p, s, e: task.update_progress(p, s, e)
                )
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")
            
            task.result = result
            
            if result.get('success'):
                task.title = result.get('title', '未知标题')
                task.filename = result.get('filename', '')
                task.status = "已完成"
                task.progress = 100
            else:
                task.status = "失败"
                task.progress = 0
        
        except Exception as e:
            task.status = "失败"
            task.progress = 0
            print(f"任务执行出错: {str(e)}")
    
    def cancel_task(self, task_id: str) -> bool:
        """取消下载任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        if task.status == "等待中":
            # 如果任务还在队列中，直接标记为取消
            task.cancel()
            return True
        elif task.status == "下载中":
            # 如果任务正在下载，标记为取消
            # 注意：yt-dlp 不直接支持取消，任务会在下一个进度回调时检测到取消状态
            task.cancel()
            self.downloader.cancel_download()
            return True
        
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """暂停下载任务 (预留接口，yt-dlp 不直接支持暂停)"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == "下载中":
            task.status = "已暂停"
            # 实际暂停逻辑需要在 yt-dlp 支持后实现
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """恢复下载任务 (预留接口，yt-dlp 不直接支持恢复)"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == "已暂停":
            task.status = "等待中"
            self.task_queue.put(task_id)
            
            # 如果工作线程未运行，启动它
            if not self.running:
                self.start_worker()
            
            return True
        return False
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务列表"""
        return list(self.tasks.values())


class TaskFrame(ctk.CTkFrame):
    """任务列表框架"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 配置网格布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 创建表头
        headers_frame = ctk.CTkFrame(self)
        headers_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5,0))
        
        headers = [
            ("标题", 200), 
            ("类型", 80), 
            ("进度", 100), 
            ("状态", 80), 
            ("速度", 100), 
            ("剩余时间", 100), 
            ("操作", 80)
        ]
        
        for i, (header, width) in enumerate(headers):
            label = ctk.CTkLabel(headers_frame, text=header, width=width)
            label.grid(row=0, column=i, padx=5, pady=5, sticky="w")
        
        # 任务列表框架
        self.tasks_frame = ctk.CTkScrollableFrame(self)
        self.tasks_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # 任务行
        self.task_rows = {}
        
    def update_tasks(self, tasks):
        """更新任务列表"""
        # 清除旧行
        for widget in self.tasks_frame.winfo_children():
            widget.destroy()
        
        # 添加新行
        for i, task in enumerate(tasks):
            # 标题
            title_label = ctk.CTkLabel(self.tasks_frame, text=task.title[:30], width=200)
            title_label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            
            # 类型
            type_label = ctk.CTkLabel(self.tasks_frame, text=task.task_type, width=50)
            type_label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            
            # 进度条
            progress_bar = ctk.CTkProgressBar(self.tasks_frame, width=100)
            progress_bar.grid(row=i, column=2, padx=5, pady=2)
            progress_bar.set(task.progress / 100)
            
            # 状态
            status_label = ctk.CTkLabel(self.tasks_frame, text=task.status, width=70)
            status_label.grid(row=i, column=3, padx=5, pady=2, sticky="w")
            
            # 速度
            speed_label = ctk.CTkLabel(self.tasks_frame, text=task.speed, width=100)
            speed_label.grid(row=i, column=4, padx=5, pady=2, sticky="w")
            
            # 剩余时间
            eta_label = ctk.CTkLabel(self.tasks_frame, text=task.eta, width=70)
            eta_label.grid(row=i, column=5, padx=5, pady=2, sticky="w")
            
            # 添加操作按钮
            if task.status in ["等待中", "下载中"]:
                cancel_btn = ctk.CTkButton(
                    self.tasks_frame, text="取消", width=60,
                    command=lambda t=task.id: self.master.cancel_task(t)
                )
                cancel_btn.grid(row=i, column=6, padx=5, pady=2)
            
            # 保存行引用
            self.task_rows[task.id] = {
                "title": title_label,
                "type": type_label,
                "progress": progress_bar,
                "status": status_label,
                "speed": speed_label,
                "eta": eta_label,
                "row": i
            }


class YouTubeDownloaderGUI(ctk.CTk):
    """YouTube 下载器图形界面"""
    
    def __init__(self):
        """初始化图形界面"""
        super().__init__()
        
        self.title("YouTube 下载器")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        self.manager = DownloadManager()
        
        # 加载设置
        self.settings_file = os.path.expanduser('~/Documents/youtube_downloader_settings.json')
        self.settings = self._load_settings()
        
        # 移除 self.selected_task_id
        
        # 创建界面
        self.create_widgets()
        
        # 启动更新线程
        self.update_thread = threading.Thread(target=self._update_ui, daemon=True)
        self.update_thread.start()
    
    def _load_settings(self):
        """加载设置"""
        default_settings = {
            'save_path': os.path.expanduser('~/Downloads'),
            'default_resolution': 'best',
            'default_audio_format': 'mp3',
            'default_subtitle_lang': 'zh-CN'
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 确保所有默认设置都存在
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
        except Exception as e:
            print(f"加载设置出错: {str(e)}")
        
        return default_settings
    
    def _save_settings(self, window, save_path, resolution, audio_format, subtitle_lang):
        """保存设置"""
        self.settings['save_path'] = save_path
        self.settings['default_resolution'] = resolution
        self.settings['default_audio_format'] = audio_format
        self.settings['default_subtitle_lang'] = subtitle_lang
        
        # 更新主窗口中的保存路径
        self.save_path_entry.delete(0, 'end')
        self.save_path_entry.insert(0, save_path)
        
        # 保存到文件
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设置出错: {str(e)}")
        
        # 关闭设置窗口
        window.destroy()
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部输入区
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        url_label = ctk.CTkLabel(input_frame, text="YouTube 链接:")
        url_label.pack(side="left", padx=5)
        
        self.url_entry = ctk.CTkEntry(input_frame, width=600)  # 加宽输入框
        self.url_entry.pack(side="left", padx=5)
        
        # 下载按钮区（新的frame）
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        download_video_btn = ctk.CTkButton(
            button_frame, text="下载视频", 
            command=lambda: self.add_download_task("video"),
            width=120  # 统一按钮宽度
        )
        download_video_btn.pack(side="left", padx=5)
        
        download_audio_btn = ctk.CTkButton(
            button_frame, text="下载音频", 
            command=lambda: self.add_download_task("audio"),
            width=120
        )
        download_audio_btn.pack(side="left", padx=5)
        
        download_subtitle_btn = ctk.CTkButton(
            button_frame, text="下载字幕", 
            command=lambda: self.add_download_task("subtitle"),
            width=120
        )
        download_subtitle_btn.pack(side="left", padx=5)
        
        # 中间任务列表区
        task_label = ctk.CTkLabel(self, text="下载队列", font=("Arial", 14, "bold"))
        task_label.pack(anchor="w", padx=15, pady=(10, 0))
        
        self.task_frame = TaskFrame(self)
        self.task_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 删除整个 control_frame 部分
        
        # 设置区
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        save_path_label = ctk.CTkLabel(settings_frame, text="保存路径:")
        save_path_label.pack(side="left", padx=5)
        
        self.save_path_entry = ctk.CTkEntry(settings_frame, width=300)
        self.save_path_entry.pack(side="left", padx=5)
        self.save_path_entry.insert(0, self.settings['save_path'])
        
        open_folder_btn = ctk.CTkButton(
            settings_frame, text="打开文件夹", 
            command=self.open_folder
        )
        open_folder_btn.pack(side="left", padx=5)
        
        browse_btn = ctk.CTkButton(
            settings_frame, text="更改保存路径", 
            command=self.browse_save_path
        )
        browse_btn.pack(side="left", padx=5)
        
        settings_btn = ctk.CTkButton(
            settings_frame, text="设置", 
            command=self.show_settings_window
        )
        settings_btn.pack(side="left", padx=5)
    
    def add_download_task(self, task_type):
        """添加下载任务"""
        url = self.url_entry.get().strip()
        if not url:
            return
        
        # 创建任务
        task = DownloadTask(
            url=url,
            task_type=task_type,
            options={
                'resolution': self.settings['default_resolution'],
                'format': self.settings['default_audio_format'],
                'language': self.settings['default_subtitle_lang']
            },
            save_path=self.settings['save_path']
        )
        
        # 添加到管理器
        self.manager.add_task(task)
        
        # 清空输入框
        self.url_entry.delete(0, 'end')
    
    def _update_ui(self):
        """更新UI的线程函数"""
        while True:
            try:
                # 获取所有任务
                tasks = self.manager.get_all_tasks()
                
                # 在主线程中更新UI
                self.after(100, lambda t=tasks: self.task_frame.update_tasks(t))
                
                time.sleep(0.5)
            except Exception as e:
                print(f"UI更新错误: {str(e)}")
                time.sleep(1)
    
    def pause_task(self):
        """暂停选中的任务"""
        if self.selected_task_id:
            self.manager.pause_task(self.selected_task_id)
    
    def resume_task(self):
        """恢复选中的任务"""
        if self.selected_task_id:
            self.manager.resume_task(self.selected_task_id)
    
    def cancel_task(self, task_id=None):
        """取消选中的任务"""
        if task_id is None:
            task_id = self.selected_task_id
            
        if task_id:
            if self.manager.cancel_task(task_id):
                print(f"任务已取消: {task_id}")
            else:
                print(f"无法取消任务: {task_id}")
    
    def open_folder(self):
        """打开下载文件夹"""
        import subprocess
        import platform
        
        path = self.settings['save_path']
        
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux
            subprocess.run(["xdg-open", path])
    
    def browse_save_path(self):
        """浏览并选择保存路径"""
        from tkinter import filedialog
        
        folder = filedialog.askdirectory(initialdir=self.settings['save_path'])
        if folder:
            self.settings['save_path'] = folder
            self.save_path_entry.delete(0, 'end')
            self.save_path_entry.insert(0, folder)
            
            # 保存设置
            try:
                os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(self.settings, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存设置出错: {str(e)}")
    
    def show_settings_window(self):
        """显示设置窗口"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("设置")
        settings_window.geometry("500x300")
        settings_window.resizable(False, False)
        settings_window.grab_set()  # 模态窗口
        
        # 设置内容
        frame = ctk.CTkFrame(settings_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 保存路径
        path_frame = ctk.CTkFrame(frame)
        path_frame.pack(fill="x", pady=10)
        
        path_label = ctk.CTkLabel(path_frame, text="保存路径:")
        path_label.pack(side="left", padx=5)
        
        path_entry = ctk.CTkEntry(path_frame, width=300)
        path_entry.pack(side="left", padx=5)
        path_entry.insert(0, self.settings['save_path'])
        
        path_btn = ctk.CTkButton(
            path_frame, text="更改路径", 
            command=lambda: self._browse_path_in_settings(path_entry)
        )
        path_btn.pack(side="left", padx=5)
        
        # 视频分辨率
        res_frame = ctk.CTkFrame(frame)
        res_frame.pack(fill="x", pady=10)
        
        res_label = ctk.CTkLabel(res_frame, text="默认视频分辨率:")
        res_label.pack(side="left", padx=5)
        
        res_var = ctk.StringVar(value=self.settings['default_resolution'])
        res_combo = ctk.CTkComboBox(
            res_frame, values=["best", "1080p", "720p"], 
            variable=res_var, width=150
        )
        res_combo.pack(side="left", padx=5)
        
        # 音频格式
        audio_frame = ctk.CTkFrame(frame)
        audio_frame.pack(fill="x", pady=10)
        
        audio_label = ctk.CTkLabel(audio_frame, text="默认音频格式:")
        audio_label.pack(side="left", padx=5)
        
        audio_var = ctk.StringVar(value=self.settings['default_audio_format'])
        audio_combo = ctk.CTkComboBox(
            audio_frame, values=["mp3", "m4a"], 
            variable=audio_var, width=150
        )
        audio_combo.pack(side="left", padx=5)
        
        # 字幕语言
        sub_frame = ctk.CTkFrame(frame)
        sub_frame.pack(fill="x", pady=10)
        
        sub_label = ctk.CTkLabel(sub_frame, text="默认字幕语言:")
        sub_label.pack(side="left", padx=5)
        
        sub_var = ctk.StringVar(value=self.settings['default_subtitle_lang'])
        sub_combo = ctk.CTkComboBox(
            sub_frame, values=["en", "zh-CN", "ja", "ko"], 
            variable=sub_var, width=150
        )
        sub_combo.pack(side="left", padx=5)
        
        # 按钮
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=20)
        
        save_btn = ctk.CTkButton(
            btn_frame, text="保存", 
            command=lambda: self._save_settings(
                settings_window, path_entry.get(), 
                res_var.get(), audio_var.get(), sub_var.get()
            )
        )
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="取消", 
            command=settings_window.destroy
        )
        cancel_btn.pack(side="left", padx=10)
    
    def _browse_path_in_settings(self, entry_widget):
        """在设置窗口中浏览路径"""
        from tkinter import filedialog
        
        folder = filedialog.askdirectory(initialdir=entry_widget.get())
        if folder:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, folder)