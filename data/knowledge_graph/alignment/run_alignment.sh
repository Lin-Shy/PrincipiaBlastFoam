#!/bin/bash
# 知识图谱对齐一键运行脚本

# 设置颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}知识图谱对齐工具 - 一键运行${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 检查当前目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${YELLOW}项目根目录: ${PROJECT_ROOT}${NC}"
echo ""

# 步骤 1: 运行对齐工具
echo -e "${GREEN}步骤 1/2: 运行对齐工具${NC}"
echo -e "${BLUE}----------------------------------------${NC}"
python3 "${SCRIPT_DIR}/align_knowledge_graphs_v1.py"

ALIGN_EXIT_CODE=$?

if [ $ALIGN_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ 对齐完成！${NC}\n"
    
    # 步骤 2: 运行测试验证
    echo -e "${GREEN}步骤 2/2: 验证对齐结果${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
    python3 "${SCRIPT_DIR}/test_alignment.py"
    
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}================================${NC}"
        echo -e "${GREEN}🎉 对齐和验证全部完成！${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo -e "${YELLOW}输出文件位置:${NC}"
        echo -e "  • User Guide (对齐后):"
        echo -e "    ${BLUE}data/knowledge_graph/user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json${NC}"
        echo ""
        echo -e "  • Tutorial Graph (对齐后):"
        echo -e "    ${BLUE}data/knowledge_graph/tutorial_knowledge_graph/aligned_tutorial_knowledge_graph.json${NC}"
        echo ""
        echo -e "  • Case Content (对齐后):"
        echo -e "    ${BLUE}data/knowledge_graph/case_content_knowledge_graph_aligned/*.json${NC}"
        echo ""
        echo -e "${YELLOW}下一步操作:${NC}"
        echo -e "  1. 查看对齐报告（已在上方显示）"
        echo -e "  2. 更新检索器以使用对齐数据"
        echo -e "  3. 参考文档: ${BLUE}data/knowledge_graph/ALIGNMENT_USAGE_GUIDE.md${NC}"
        echo ""
        exit 0
    else
        echo -e "\n${RED}✗ 验证过程出现错误${NC}"
        exit $TEST_EXIT_CODE
    fi
else
    echo -e "\n${RED}✗ 对齐过程出现错误${NC}"
    echo -e "${YELLOW}请检查错误信息并重试${NC}"
    exit $ALIGN_EXIT_CODE
fi
