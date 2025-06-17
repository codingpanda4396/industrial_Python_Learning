import os
import shutil

def organize_files():
    print("文件整理器")
    print("输入需要整理的源路径")
    src = input().strip()  # 移除可能的空格
    print("输入整理后的目标路径")
    dst = input().strip()
    
    # 检查路径是否存在
    if not os.path.exists(src):
        print(f"错误：源路径不存在 - {src}")
        return
    if not os.path.isdir(src):
        print(f"错误：源路径不是目录 - {src}")
        return
        
    print(f"正在整理 {src} 到 {dst}...")
    
    # 创建目标根目录（如果不存在）
    os.makedirs(dst, exist_ok=True)
    print(f"已创建目标根目录: {dst}")

    file_count = 0
    move_count = 0
    dir_created_count = 0
    conflict_count = 0
    created_categories = set()  # 跟踪已创建的扩展名文件夹
    
    # 使用os.walk遍历目录
    for dirpath, dirnames, filenames in os.walk(src):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            
            # 确保是文件而不是目录
            if not os.path.isfile(file_path):
                continue
            
            file_count += 1
            
            # 获取文件扩展名
            _, ext = os.path.splitext(filename)
            # 处理没有扩展名的情况
            category = ext[1:].lower() if ext else "无扩展名"
            
            # 创建分类目录
            category_dir = os.path.join(dst, category)
            if category not in created_categories:
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir, exist_ok=True)
                    print(f"[创建目录] {category_dir}")
                    created_categories.add(category)
                    dir_created_count += 1
            
            # 构造目标路径
            dst_path = os.path.join(category_dir, filename)
            
            # 处理文件名冲突
            if os.path.exists(dst_path):
                base_name = os.path.splitext(filename)[0]
                conflict_suffix = 1
                while True:
                    new_filename = f"{base_name}_{conflict_suffix}{ext}" if ext else f"{base_name}_{conflict_suffix}"
                    new_dst_path = os.path.join(category_dir, new_filename)
                    if not os.path.exists(new_dst_path):
                        dst_path = new_dst_path
                        conflict_count += 1
                        print(f"[冲突解决] 重命名: {filename} -> {new_filename}")
                        break
                    conflict_suffix += 1
            
            # 移动文件（使用shutil.move更安全）
            try:
                shutil.move(file_path, dst_path)
                move_count += 1
                print(f"[移动文件] {file_path} -> {dst_path}")
            except Exception as e:
                print(f"移动文件失败: {file_path} -> {dst_path}")
                print(f"错误信息: {str(e)}")
    
    # 总结报告
    print("\n====== 整理完成! ======")
    print(f"扫描文件总数: {file_count}")
    print(f"创建分类目录: {dir_created_count}个")
    print(f"成功移动文件: {move_count}个")
    print(f"解决文件名冲突: {conflict_count}个")
    print(f"处理失败: {file_count - move_count}个")

if __name__ == "__main__":
    organize_files()