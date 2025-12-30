#!/usr/bin/env python3
"""
从合并的OpenFOAM probes数据中提取各测点的超压峰值
超压峰值 = 最大压强 - 101298 Pa（大气压）
"""

import os
from pathlib import Path
import numpy as np


def extract_peak_overpressure(merged_probes_dir, output_dir=None, atmospheric_pressure=101298):
    """
    从合并的probe数据中提取各测点的超压峰值
    
    参数:
        merged_probes_dir: 合并后的probes文件夹路径
        output_dir: 输出文件夹路径，默认与merged_probes_dir相同
        atmospheric_pressure: 大气压值，默认101298 Pa
    """
    merged_path = Path(merged_probes_dir)
    
    if output_dir is None:
        output_dir = merged_path
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找所有物理量文件
    field_files = [f for f in merged_path.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    if not field_files:
        print("未找到合并的probe数据文件")
        return
    
    print(f"找到 {len(field_files)} 个物理量文件")
    
    # 对每个物理量处理
    for field_file in field_files:
        field_name = field_file.name
        print(f"\n处理物理量: {field_name}")
        
        # 读取文件
        with open(field_file, 'r') as f:
            lines = f.readlines()
        
        # 提取测点位置信息
        probe_info_lines = []
        data_lines = []
        
        for line in lines:
            if line.strip().startswith('# Probe'):
                probe_info_lines.append(line)
            elif not line.strip().startswith('#') and line.strip():
                data_lines.append(line.strip())
        
        if not data_lines:
            print(f"  警告: {field_name} 中没有数据")
            continue
        
        # 获取测点数量
        num_probes = len(probe_info_lines)
        print(f"  测点数量: {num_probes}")
        
        # 解析数据，计算每个测点的峰值
        peak_values = [-float('inf')] * num_probes
        
        for line in data_lines:
            parts = line.split()
            if len(parts) > 1:
                # 第一列是时间，从第二列开始是各测点的值
                for i in range(min(num_probes, len(parts) - 1)):
                    try:
                        value = float(parts[i + 1])
                        # 跳过无效值（如 -1.79769313486e+307）
                        if value > -1e300:
                            peak_values[i] = max(peak_values[i], value)
                    except ValueError:
                        continue
        
        # 计算超压峰值（峰值 - 大气压）
        peak_overpressures = []
        for peak in peak_values:
            if peak > -float('inf'):
                overpressure = peak - atmospheric_pressure
                peak_overpressures.append(overpressure)
            else:
                # 如果没有有效数据，记录为0
                peak_overpressures.append(0.0)
        
        # 写入输出文件
        output_file = output_dir / f"{field_name}_peak_overpressure"
        with open(output_file, 'w') as f:
            # 写入测点位置信息
            for line in probe_info_lines:
                f.write(line)
            
            # 写入表头
            f.write("# Probe ID         Peak Overpressure (Pa)\n")
            
            # 写入各测点的超压峰值
            for i, overpressure in enumerate(peak_overpressures):
                f.write(f"{i:<20}{overpressure:<20.8e}\n")
        
        print(f"  已保存到: {output_file}")
        print(f"  超压峰值范围: {min(peak_overpressures):.2e} ~ {max(peak_overpressures):.2e} Pa")
        
        # 统计信息
        valid_count = sum(1 for p in peak_overpressures if p > 0)
        print(f"  有效测点数: {valid_count}/{num_probes}")
    
    print(f"\n所有峰值文件已保存到: {output_dir}")


if __name__ == "__main__":
    # 设置合并后的probes文件夹路径
    merged_probes_dir = "/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/surfaceburst_100kg/postProcessing/merged_probes"
    
    # 执行提取
    extract_peak_overpressure(merged_probes_dir)
    
    print("\n提取完成！")
