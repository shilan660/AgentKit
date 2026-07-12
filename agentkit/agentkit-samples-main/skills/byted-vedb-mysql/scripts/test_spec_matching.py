#!/usr/bin/env python3
# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" specific language governing permissions and
# limitations under the License.

"""
测试规格匹配功能
"""

import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入我们的函数
from create_vedbm_instance import (
    AVAILABLE_SPECS,
    DEFAULT_SPEC,
    parse_spec_input,
    find_closest_spec,
)

print("=" * 70)
print("🧪 测试规格匹配功能")
print("=" * 70)
print()

# 显示可用规格
print("📋 可用规格：")
for spec in AVAILABLE_SPECS:
    print(f"  - {spec['description']}: {spec['name']}")
print()

# 测试用例
test_cases = [
    # (输入, 期望描述)
    ("", "默认规格"),
    ("2c8g", "精确匹配 2核8GB"),
    ("4c16g", "精确匹配 4核16GB"),
    ("8c32g", "精确匹配 8核32GB"),
    ("16c64g", "精确匹配 16核64GB"),
    ("vedb.mysql.x2.large", "完整规格名 2核8GB"),
    ("vedb.mysql.x4.large", "完整规格名 4核16GB"),
    ("3c10g", "智能匹配（接近 4核16GB）"),
    ("5c20g", "智能匹配（接近 8核32GB）"),
    ("1c4g", "智能匹配（最小规格 2核8GB）"),
    ("20c100g", "智能匹配（最大规格 16核64GB）"),
    ("2c", "只指定 CPU 2核"),
    ("4c", "只指定 CPU 4核"),
    ("8g", "只指定内存 8GB"),
    ("16g", "只指定内存 16GB"),
    ("invalid-spec", "无效规格，使用默认"),
]

print("🧪 开始测试：")
print("-" * 70)

all_passed = True

for spec_input, description in test_cases:
    print(f"\n测试输入: '{spec_input}' ({description})")

    result = parse_spec_input(spec_input) if spec_input else DEFAULT_SPEC

    if result:
        print(f"  ✅ 匹配结果: {result['description']} ({result['name']})")
    else:
        result = find_closest_spec()
        print(f"  ⚠️  无法解析，使用默认: {result['description']} ({result['name']})")

print("\n" + "=" * 70)
print("✅ 测试完成！")
print("=" * 70)
