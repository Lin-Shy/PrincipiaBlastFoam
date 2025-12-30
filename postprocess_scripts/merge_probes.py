#!/usr/bin/env python3
"""
合并OpenFOAM probes数据文件
将不同时间步的probe数据整合成单个文件（每个物理量一个文件）
"""

import os
import re
from pathlib import Path
import numpy as np


def read_probe_file(filepath):
    """读取单个probe文件，返回数据"""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # 跳过注释行
    data_lines = [line for line in lines if not line.strip().startswith('#')]
    
    if not data_lines:
        return None
    
    # 解析数据
    data = []
    for line in data_lines:
        if line.strip():
            data.append(line.strip())
    
    return data


def merge_probes(probes_dir, output_dir=None):
    """
    合并probes文件夹中的数据
    
    参数:
        probes_dir: probes文件夹路径
        output_dir: 输出文件夹路径，默认为probes_dir的父目录
    """
    probes_path = Path(probes_dir)
    
    if output_dir is None:
        output_dir = probes_path.parent / 'merged_probes'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有时间文件夹，按数值排序
    time_dirs = []
    for item in probes_path.iterdir():
        if item.is_dir():
            try:
                time_value = float(item.name)
                time_dirs.append((time_value, item))
            except ValueError:
                continue
    
    time_dirs.sort(key=lambda x: x[0])
    
    if not time_dirs:
        print("未找到时间文件夹")
        return
    
    # 获取所有物理量（从第一个时间文件夹获取）
    first_time_dir = time_dirs[0][1]
    field_files = [f.name for f in first_time_dir.iterdir() if f.is_file()]
    
    print(f"找到 {len(time_dirs)} 个时间步")
    print(f"找到 {len(field_files)} 个物理量: {', '.join(field_files)}")
    
    # 对每个物理量进行合并
    for field in field_files:
        print(f"\n处理物理量: {field}")
        
        merged_data = []
        probe_info_lines = []
        time_header_line = ""
        
        for time_value, time_dir in time_dirs:
            field_file = time_dir / field
            
            if not field_file.exists():
                print(f"  警告: {field_file} 不存在，跳过")
                continue
            
            # 读取文件
            with open(field_file, 'r') as f:
                lines = f.readlines()
            
            # 提取测点信息和表头（仅第一次）
            if not probe_info_lines:
                for line in lines:
                    if line.strip().startswith('# Probe'):
                        # 测点位置信息
                        probe_info_lines.append(line)
                    elif line.strip().startswith('# Time'):
                        # 表头行
                        time_header_line = line
                    elif not line.strip().startswith('#'):
                        # 遇到非注释行，停止提取
                        break
            
            # 提取最后一行数据（物理量数据）
            data_line = None
            for line in reversed(lines):
                if not line.strip().startswith('#') and line.strip():
                    data_line = line.strip()
                    break
            
            if data_line:
                # 提取物理量值（跳过第一列的时间）
                parts = data_line.split()
                if len(parts) > 1:
                    # 第一列是原文件中的时间，从第二列开始是各测点的物理量
                    field_values = '  '.join(parts[1:])
                    merged_data.append(f"{time_value:<20.8e}{field_values}\n")
                else:
                    print(f"  警告: {field_file} 数据格式异常")
        
        # 写入合并后的文件
        output_file = output_dir / field
        with open(output_file, 'w') as f:
            # 写入测点位置信息
            for line in probe_info_lines:
                f.write(line)
            
            # 写入表头
            f.write(time_header_line)
            
            # 写入数据
            for data_line in merged_data:
                f.write(data_line)
        
        print(f"  已保存到: {output_file}")
        print(f"  共 {len(merged_data)} 行数据")
    
    print(f"\n所有文件已保存到: {output_dir}")


if __name__ == "__main__":
    # 设置probes文件夹路径
    probes_dir = "/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/surfaceburst_100kg/postProcessing/probes"
    
    # 执行合并
    merge_probes(probes_dir)
    
    print("\n合并完成！")