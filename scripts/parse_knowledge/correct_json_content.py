import json
import argparse
import os


def correct_text(text):
    # 添加更多矫正规则可扩展
    corrections = {
        '\uFB00': 'ff',  # ﬀ 连体
        '\uFB01': 'fi',  # ﬁ 连体
        '\uFB02': 'fl',  # ﬂ 连体
        '\uFB03': 'ffi', # ﬃ 连体
        '\uFB04': 'ffl', # ﬄ 连体
        '\uFB05': 'ft',  # ﬅ 连体
        '\uFB06': 'st',  # ﬆ 连体
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return text


def correct_json_file(json_path, output_path=None):
    if not os.path.isfile(json_path):
        print(f"JSON文件不存在: {json_path}")
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for node in data.get('nodes', []):
        node['title'] = correct_text(node.get('title', ''))
        node['content'] = correct_text(node.get('content', ''))
    if output_path is None:
        output_path = json_path.replace('.json', '_corrected.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已修正内容并保存到: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='修正知识图谱JSON中的错误字符')
    parser.add_argument('-json', type=str,
                        default=r'D:\SYSU-Projects\LLM\PrincipiaBlastFoam\data/knowledge_graph/database/blastfoam_knowledge'
                                r'.json',
                        help='知识图谱JSON文件路径')
    parser.add_argument('-output', type=str, default=None, help='修正后输出文件路径')
    args = parser.parse_args()
    correct_json_file(args.json, args.output)


if __name__ == '__main__':
    main()
