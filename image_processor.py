import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os
from tkinterdnd2 import DND_FILES, TkinterDnD

class ImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("图片裁剪与边框添加工具")
        self.root.geometry("1500x900")
        self.root.minsize(800, 600)
        
        # 设置中文字体支持
        self.font = ("SimHei", 10)
        
        # 初始化变量
        self.original_image = None
        self.processed_image = None
        self.image_path = None
        self.canvas_image = None
        self.start_x = self.start_y = 0
        self.rect = None
        self.drag_data = {}
        self.current_ratio = "4:3"
        
        # 批量处理相关变量
        self.image_queue = []  # 存储待处理的图片路径队列
        
        # 创建主框架
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建工具栏
        self.toolbar = tk.Frame(self.main_frame, bd=1, relief=tk.RAISED)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # 添加按钮
        self.load_btn = tk.Button(self.toolbar, text="加载图片", command=self.load_image, font=self.font)
        self.load_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加比例切换按钮
        self.ratio_var = tk.StringVar(value="4:3")
        self.ratio_frame = tk.Frame(self.toolbar)
        self.ratio_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Label(self.ratio_frame, text="裁剪比例:", font=self.font).pack(side=tk.LEFT)
        self.ratio_43 = tk.Radiobutton(self.ratio_frame, text="4:3", variable=self.ratio_var, value="4:3", 
                                     command=self.change_ratio, font=self.font)
        self.ratio_43.pack(side=tk.LEFT)
        self.ratio_34 = tk.Radiobutton(self.ratio_frame, text="3:4", variable=self.ratio_var, value="3:4", 
                                     command=self.change_ratio, font=self.font)
        self.ratio_34.pack(side=tk.LEFT)
       # 添加导出按钮
        self.export_btn = tk.Button(self.toolbar, text="导出图片", command=self.export_image, font=self.font)
        self.export_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 添加跳过按钮
        self.skip_btn = tk.Button(self.toolbar, text="跳过图片", command=self.skip_image, font=self.font)
        self.skip_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 创建中间的内容框架（包含图片显示区域和右侧队列）
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建图片显示框架
        self.image_frame = tk.Frame(self.content_frame, bd=1, relief=tk.SUNKEN)
        self.image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        self.v_scroll = tk.Scrollbar(self.image_frame, orient=tk.VERTICAL)
        self.h_scroll = tk.Scrollbar(self.image_frame, orient=tk.HORIZONTAL)
        
        # 创建画布
        self.canvas = tk.Canvas(self.image_frame, bd=0, 
                               xscrollcommand=self.h_scroll.set,
                               yscrollcommand=self.v_scroll.set)
        
        # 配置滚动条
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)
        
        # 布局画布和滚动条
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加提示文本
        self.info_text = tk.Label(self.image_frame, text="请拖拽图片到此处或点击'加载图片'按钮", 
                                 font=(self.font[0], 12), fg="gray")
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定拖放事件
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self.on_drop)
        
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        
        # 创建右侧的图片队列列表
        self.queue_frame = tk.Frame(self.content_frame, bd=1, relief=tk.SUNKEN, width=250)
        self.queue_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # 队列标题
        tk.Label(self.queue_frame, text="待处理图片队列", font=(self.font[0], 11, "bold"), pady=10).pack(side=tk.TOP, fill=tk.X, padx=10)
        
        # 队列列表框
        self.queue_listbox = tk.Listbox(self.queue_frame, font=self.font, selectmode=tk.SINGLE, width=30, height=20)
        self.queue_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        # 绑定列表选择事件
        self.queue_listbox.bind('<<ListboxSelect>>', self.on_queue_select)
        
        # 队列信息标签
        self.queue_info = tk.Label(self.queue_frame, text="队列中无图片", font=self.font, fg="gray")
        self.queue_info.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
    
    def load_image(self):
        """加载多张图片"""
        file_paths = filedialog.askopenfilenames(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if file_paths:
            # 将选中的图片添加到队列
            self.image_queue.extend(file_paths)
            
            # 更新队列列表显示
            self.update_queue_display()
            
            # 如果当前没有图片正在处理，立即处理第一张
            if not self.original_image:
                next_image_path = self.image_queue.pop(0)
                self.process_image(next_image_path)
    
    def on_drop(self, event):
        """处理拖放事件"""
        file_paths = event.data
        # 处理Windows路径格式（去掉大括号）
        if file_paths.startswith("{"):
            # 检查是否包含多个文件（有多个花括号）
            if "}" in file_paths[1:]:
                # 分割多个文件路径
                file_paths = file_paths[1:-1].split("} {")
            else:
                file_paths = [file_paths[1:-1]]
        else:
            file_paths = [file_paths]
        
        # 处理每个文件路径
        valid_images = []
        for file_path in file_paths:
            # 处理空格转义
            file_path = file_path.replace("\\ ", " ")
            # 检查是否为图片文件
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                valid_images.append(file_path)
        
        if valid_images:
            # 将有效的图片添加到队列
            self.image_queue.extend(valid_images)
            
            # 更新队列列表显示
            self.update_queue_display()
            
            # 如果当前没有图片正在处理，立即处理第一张
            if not self.original_image:
                next_image_path = self.image_queue.pop(0)
                self.process_image(next_image_path)
        else:
            messagebox.showerror("错误", "请拖拽有效的图片文件")
    
    def process_image(self, file_path):
        """处理图片"""
        try:
            # 隐藏提示文本
            self.info_text.pack_forget()
            
            # 加载图片
            self.image_path = file_path
            self.original_image = Image.open(file_path)
            
            # 更新队列列表显示
            self.update_queue_display()
            
            # 计算合适的显示尺寸
            self.display_image()
            
            # 创建初始裁剪框
            self.create_initial_rect()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {str(e)}")
    
    def display_image(self):
        """在画布上显示图片"""
        # 获取画布尺寸
        canvas_width = self.canvas.winfo_width() - 20
        canvas_height = self.canvas.winfo_height() - 20
        
        # 计算缩放比例
        img_width, img_height = self.original_image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        
        # 调整图片大小
        self.display_width = int(img_width * scale)
        self.display_height = int(img_height * scale)
        resized_image = self.original_image.resize((self.display_width, self.display_height), Image.LANCZOS)
        
        # 转换为Tkinter可用的图片格式
        self.canvas_image = ImageTk.PhotoImage(resized_image)
        
        # 清空画布并显示图片（居中显示）
        self.canvas.delete("all")
        self.canvas.create_image(self.display_width//2, self.display_height//2, image=self.canvas_image, anchor=tk.CENTER)
        
        # 设置画布滚动区域（确保覆盖整个图片）
        self.canvas.config(scrollregion=(0, 0, self.display_width, self.display_height))
    
    def change_ratio(self):
        """切换裁剪比例"""
        self.current_ratio = self.ratio_var.get()
        if self.original_image:
            self.create_initial_rect()
            # 确保切换比例后裁剪框不超出范围
            self.constrain_rect()
    
    def create_initial_rect(self):
        """创建初始的裁剪框，确保4:3横长，3:4竖长，且不超过图片原始尺寸"""
        if not self.original_image:
            return
        
        # 获取当前比例
        is_4_3 = (self.current_ratio == "4:3")
        
        # 计算裁剪框的大小
        img_width, img_height = self.original_image.size
        
        if is_4_3:
            # 4:3比例 - 始终横长（宽度 > 高度）
            # 计算最大可能的裁剪尺寸，不超过图片原始尺寸
            if (img_width / img_height) >= 4/3:
                # 图片比4:3更宽，以图片高度为基准
                max_crop_height = img_height
                max_crop_width = int(max_crop_height * 4/3)
                # 确保宽度不超过图片宽度
                max_crop_width = min(max_crop_width, img_width)
                max_crop_height = int(max_crop_width * 3/4)
            else:
                # 图片比4:3更窄，以图片宽度为基准
                max_crop_width = img_width
                max_crop_height = int(max_crop_width * 3/4)
                # 确保高度不超过图片高度
                max_crop_height = min(max_crop_height, img_height)
                max_crop_width = int(max_crop_height * 4/3)
        else:
            # 3:4比例 - 始终竖长（高度 > 宽度）
            if (img_width / img_height) <= 3/4:
                # 图片比3:4更窄，以图片宽度为基准
                max_crop_width = img_width
                max_crop_height = int(max_crop_width * 4/3)
                # 确保高度不超过图片高度
                max_crop_height = min(max_crop_height, img_height)
                max_crop_width = int(max_crop_height * 3/4)
            else:
                # 图片比3:4更宽，以图片高度为基准
                max_crop_height = img_height
                max_crop_width = int(max_crop_height * 3/4)
                # 确保宽度不超过图片宽度
                max_crop_width = min(max_crop_width, img_width)
                max_crop_height = int(max_crop_width * 4/3)
        
        # 计算显示尺寸
        scale_x = self.display_width / img_width
        scale_y = self.display_height / img_height
        
        display_crop_width = int(max_crop_width * scale_x)
        display_crop_height = int(max_crop_height * scale_y)
        
        # 计算裁剪框位置（居中）
        x1 = (self.display_width - display_crop_width) // 2
        y1 = (self.display_height - display_crop_height) // 2
        x2 = x1 + display_crop_width
        y2 = y1 + display_crop_height
        
        # 清除现有裁剪框
        if self.rect:
            self.canvas.delete(self.rect)
        
        # 创建新的裁剪框
        self.rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2, fill="", stipple="gray50")
        
        # 保存裁剪框信息
        self.crop_info = {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "width": max_crop_width, "height": max_crop_height,
            "ratio": 4/3 if is_4_3 else 3/4
        }
        
        # 添加调整手柄
        self.add_resize_handles()
    
    def add_resize_handles(self):
        """添加裁剪框调整手柄"""
        # 清除现有手柄
        self.canvas.delete("handle")
        
        # 获取裁剪框坐标
        x1, y1, x2, y2 = self.crop_info["x1"], self.crop_info["y1"], self.crop_info["x2"], self.crop_info["y2"]
        
        # 手柄大小（进一步增大点击区域）
        handle_size = 16
        
        # 创建八个手柄
        handles = [
            (x1 - handle_size//2, y1 - handle_size//2, x1 + handle_size//2, y1 + handle_size//2, "nw"),
            ((x1+x2)//2 - handle_size//2, y1 - handle_size//2, (x1+x2)//2 + handle_size//2, y1 + handle_size//2, "n"),
            (x2 - handle_size//2, y1 - handle_size//2, x2 + handle_size//2, y1 + handle_size//2, "ne"),
            (x1 - handle_size//2, (y1+y2)//2 - handle_size//2, x1 + handle_size//2, (y1+y2)//2 + handle_size//2, "w"),
            (x2 - handle_size//2, (y1+y2)//2 - handle_size//2, x2 + handle_size//2, (y1+y2)//2 + handle_size//2, "e"),
            (x1 - handle_size//2, y2 - handle_size//2, x1 + handle_size//2, y2 + handle_size//2, "sw"),
            ((x1+x2)//2 - handle_size//2, y2 - handle_size//2, (x1+x2)//2 + handle_size//2, y2 + handle_size//2, "s"),
            (x2 - handle_size//2, y2 - handle_size//2, x2 + handle_size//2, y2 + handle_size//2, "se")
        ]
        
        # 创建手柄并绑定事件
        for x1h, y1h, x2h, y2h, position in handles:
            handle = self.canvas.create_rectangle(x1h, y1h, x2h, y2h, fill="blue", tags=("handle", position))
            self.canvas.tag_bind(handle, "<ButtonPress-1>", lambda e, p=position: self.on_handle_press(e, p))
    
    def on_handle_press(self, event, handle_position):
        """处理手柄按下事件"""
        self.drag_data["type"] = "resize"
        self.drag_data["position"] = handle_position
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
    
    def on_button_press(self, event):
        """处理鼠标按下事件"""
        if not self.rect: return
        
        # 检查是否点击了裁剪框（检查点击点是否在裁剪框内）
        x, y = event.x, event.y
        x1, y1, x2, y2 = self.crop_info["x1"], self.crop_info["y1"], self.crop_info["x2"], self.crop_info["y2"]
        
        # 检查是否点击了裁剪框内部
        if x1 <= x <= x2 and y1 <= y <= y2:
            # 记录当前位置
            self.drag_data["type"] = "move"
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_mouse_drag(self, event):
        """处理鼠标拖拽事件"""
        if not self.rect or "type" not in self.drag_data:
            return
        
        # 计算移动距离
        delta_x = event.x - self.drag_data["x"]
        delta_y = event.y - self.drag_data["y"]
        
        # 更新拖拽数据
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        
        if self.drag_data["type"] == "move":
            # 移动裁剪框
            self.canvas.move(self.rect, delta_x, delta_y)
            self.canvas.move("handle", delta_x, delta_y)
            
            # 更新裁剪框信息
            self.crop_info["x1"] += delta_x
            self.crop_info["y1"] += delta_y
            self.crop_info["x2"] += delta_x
            self.crop_info["y2"] += delta_y
            
            # 限制裁剪框不超出图片范围
            self.constrain_rect()
        else:
            # 调整裁剪框大小
            self.resize_rect(delta_x, delta_y, self.drag_data["position"])
    
    def resize_rect(self, delta_x, delta_y, position):
        """调整裁剪框大小"""
        # 获取当前比例
        ratio = self.crop_info["ratio"]
        
        # 计算新的裁剪框坐标
        x1, y1, x2, y2 = self.crop_info["x1"], self.crop_info["y1"], self.crop_info["x2"], self.crop_info["y2"]
        
        # 根据手柄位置调整裁剪框
        if position in ["nw", "w", "sw"]:
            new_x1 = max(0, x1 + delta_x)
            if self.current_ratio == "4:3":
                delta_y = (new_x1 - x1) / ratio
            else:
                delta_y = (new_x1 - x1) * ratio
        
        if position in ["ne", "e", "se"]:
            new_x2 = min(self.display_width, x2 + delta_x)
            if self.current_ratio == "4:3":
                delta_y = (new_x2 - x2) / ratio
            else:
                delta_y = (new_x2 - x2) * ratio
        
        if position in ["nw", "n", "ne"]:
            new_y1 = max(0, y1 + delta_y)
            if self.current_ratio == "4:3":
                delta_x = (new_y1 - y1) * ratio
            else:
                delta_x = (new_y1 - y1) / ratio
        
        if position in ["sw", "s", "se"]:
            new_y2 = min(self.display_height, y2 + delta_y)
            if self.current_ratio == "4:3":
                delta_x = (new_y2 - y2) * ratio
            else:
                delta_x = (new_y2 - y2) / ratio
        
        # 根据手柄位置应用调整
        if position == "nw":
            x1 += delta_x
            y1 += delta_y
        elif position == "n":
            y1 += delta_y
        elif position == "ne":
            x2 += delta_x
            y1 += delta_y
        elif position == "w":
            x1 += delta_x
        elif position == "e":
            x2 += delta_x
        elif position == "sw":
            x1 += delta_x
            y2 += delta_y
        elif position == "s":
            y2 += delta_y
        elif position == "se":
            x2 += delta_x
            y2 += delta_y
        
        # 确保裁剪框大小合理
        min_size = 50
        if x2 - x1 < min_size or y2 - y1 < min_size:
            return
        
        # 确保不超出图片范围
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(self.display_width, x2)
        y2 = min(self.display_height, y2)
        
        # 更新裁剪框
        self.canvas.coords(self.rect, x1, y1, x2, y2)
        
        # 更新裁剪框信息
        self.crop_info["x1"] = x1
        self.crop_info["y1"] = y1
        self.crop_info["x2"] = x2
        self.crop_info["y2"] = y2
        
        # 更新调整手柄
        self.add_resize_handles()
    
    def on_button_release(self, event):
        """处理鼠标释放事件"""
        # 清除拖拽数据
        self.drag_data = {}
    
    def constrain_rect(self):
        """限制裁剪框不超出图片范围"""
        x1, y1, x2, y2 = self.crop_info["x1"], self.crop_info["y1"], self.crop_info["x2"], self.crop_info["y2"]
        
        # 计算边界
        max_x = self.display_width
        max_y = self.display_height
        
        # 调整位置
        delta_x = 0
        delta_y = 0
        
        if x1 < 0:
            delta_x = -x1
        elif x2 > max_x:
            delta_x = max_x - x2
        
        if y1 < 0:
            delta_y = -y1
        elif y2 > max_y:
            delta_y = max_y - y2
        
        # 如果需要调整
        if delta_x != 0 or delta_y != 0:
            # 移动裁剪框
            self.canvas.move(self.rect, delta_x, delta_y)
            self.canvas.move("handle", delta_x, delta_y)
            
            # 更新裁剪框信息
            self.crop_info["x1"] += delta_x
            self.crop_info["y1"] += delta_y
            self.crop_info["x2"] += delta_x
            self.crop_info["y2"] += delta_y
    
    def export_image(self):
        """导出处理后的图片并自动处理下一张"""
        if not self.original_image:
            messagebox.showwarning("警告", "请先加载图片")
            return
        
        try:
            # 计算实际裁剪区域（基于原始图片尺寸）
            scale_x = self.original_image.width / self.display_width
            scale_y = self.original_image.height / self.display_height
            
            # 转换裁剪框坐标到原始图片坐标
            orig_x1 = int(self.crop_info["x1"] * scale_x)
            orig_y1 = int(self.crop_info["y1"] * scale_y)
            orig_x2 = int(self.crop_info["x2"] * scale_x)
            orig_y2 = int(self.crop_info["y2"] * scale_y)
            
            # 确保坐标在有效范围内
            orig_x1 = max(0, orig_x1)
            orig_y1 = max(0, orig_y1)
            orig_x2 = min(self.original_image.width, orig_x2)
            orig_y2 = min(self.original_image.height, orig_y2)
            
            # 裁剪图片
            cropped_image = self.original_image.crop((orig_x1, orig_y1, orig_x2, orig_y2))
            
            # 添加固定60像素的白色边框
            border_size = {
                "left": 60,
                "right": 60,
                "top": 60,
                "bottom": 60
            }
            
            # 使用Pillow添加边框
            self.processed_image = ImageOps.expand(cropped_image, 
                                                 border=(border_size["left"], border_size["top"], 
                                                         border_size["right"], border_size["bottom"]),
                                                 fill="white")
            
            # 选择保存路径
            default_path = os.path.dirname(self.image_path) if self.image_path else os.path.join(os.path.expanduser("~"), "Desktop")
            
            # 生成NEEKO_1, NEEKO_2格式的文件名
            def get_next_neeko_filename():
                counter = 1
                while True:
                    file_name = f"NEEKO_{counter}.png"
                    file_path = os.path.join(default_path, file_name)
                    if not os.path.exists(file_path):
                        return file_name, file_path
                    counter += 1
            
            # 获取下一个可用的NEEKO文件名
            file_name, default_save_path = get_next_neeko_filename()
            
            # 获取保存路径
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")],
                initialdir=default_path,
                initialfile=file_name
            )
            
            # 保存图片
            if save_path:
                # 直接保存，不需要再次检查唯一性
                self.processed_image.save(save_path)
                messagebox.showinfo("成功", f"图片已导出到：{save_path}")
                
                # 导出完成后，清除当前图片
                self.original_image = None
                self.image_path = None
                
                # 清空画布
                self.canvas.delete("all")
                
                # 如果队列中还有图片，自动处理下一张
                if self.image_queue:
                    next_image_path = self.image_queue.pop(0)
                    self.process_image(next_image_path)
                else:
                    # 如果队列中没有图片了，显示提示文本
                    self.info_text.pack(fill=tk.BOTH, expand=True)
                    # 更新队列显示
                    self.update_queue_display()
                    
        except Exception as e:
            messagebox.showerror("错误", f"导出图片失败: {str(e)}")
    
    def skip_image(self):
        """跳过当前图片并处理下一张"""
        if not self.original_image:
            messagebox.showwarning("警告", "没有正在处理的图片")
            return
        
        # 清除当前图片
        self.original_image = None
        self.image_path = None
        
        # 清空画布
        self.canvas.delete("all")
        
        # 如果队列中还有图片，自动处理下一张
        if self.image_queue:
            next_image_path = self.image_queue.pop(0)
            self.process_image(next_image_path)
        else:
            # 如果队列中没有图片了，显示提示文本
            self.info_text.pack(fill=tk.BOTH, expand=True)
            # 更新队列显示
            self.update_queue_display()
    
    def on_queue_select(self, event):
        """处理队列列表的选择事件"""
        selection = event.widget.curselection()
        if selection:
            # 获取选中的索引
            index = selection[0]
            
            # 检查是否选中了当前正在处理的图片（索引为0）
            if index == 0 and self.image_path:
                # 如果选中的是当前图片，不做任何操作
                return
            
            # 计算实际在队列中的索引（减去当前图片的位置）
            queue_index = index - 1
            
            # 获取选中的图片路径
            if queue_index >= 0 and queue_index < len(self.image_queue):
                selected_path = self.image_queue[queue_index]
                
                # 从队列中移除该图片
                del self.image_queue[queue_index]
                
                # 如果当前有正在处理的图片，先处理它的保存
                if self.original_image:
                    # 保存当前正在处理的图片到队列末尾
                    if self.image_path and self.image_path != selected_path:
                        self.image_queue.append(self.image_path)
                    
                    # 清除当前图片
                    self.original_image = None
                    self.image_path = None
                    self.canvas.delete("all")
                
                # 处理选中的图片
                self.process_image(selected_path)
    
    def update_queue_display(self):
        """更新待处理图片队列的显示，包括当前正在编辑的图片"""
        # 清空列表框
        self.queue_listbox.delete(0, tk.END)
        
        # 先添加当前正在处理的图片（如果有）
        if self.image_path:
            current_file_name = os.path.basename(self.image_path)
            self.queue_listbox.insert(tk.END, f"● 当前：{current_file_name}")
        
        # 再添加队列中的图片
        for i, file_path in enumerate(self.image_queue):
            # 只显示文件名而不是完整路径
            file_name = os.path.basename(file_path)
            self.queue_listbox.insert(tk.END, f"{i+1}. {file_name}")
        
        # 更新队列信息
        queue_size = len(self.image_queue)
        current_size = 1 if self.image_path else 0
        total_size = current_size + queue_size
        
        if total_size == 0:
            self.queue_info.config(text="队列中无图片", fg="gray")
        else:
            status_text = "队列中共有 "
            if current_size > 0:
                status_text += f"1张正在处理 + "
            status_text += f"{queue_size}张待处理"
            self.queue_info.config(text=status_text, fg="blue")
        
        # 确保队列框架和列表框正确显示
        self.queue_frame.update_idletasks()
        self.queue_listbox.update_idletasks()
    
    def on_resize(self, event):
        """处理窗口大小变化"""
        if self.original_image:
            self.display_image()
            self.create_initial_rect()

if __name__ == "__main__":
    # 创建支持拖放的根窗口
    root = TkinterDnD.Tk()
    
    # 设置窗口图标（如果有）
    if os.path.exists("ZZZZZZ.ico"):
        root.iconbitmap("ZZZZZZ.ico")
    
    # 创建应用实例
    app = ImageProcessor(root)
    
    # 绑定窗口大小变化事件
    root.bind("<Configure>", app.on_resize)
    
    # 启动应用
    root.mainloop()