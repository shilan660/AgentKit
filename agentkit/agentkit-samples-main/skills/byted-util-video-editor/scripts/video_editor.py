#!/usr/bin/env python3

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Video Editor - 视频编辑器
支持功能：
1. 合并多个视频文件
2. 添加音频轨道（旁白、背景音乐等）
3. 视频和音频同步
4. 生成并烧录字幕（SRT格式）
5. 灵活的参数配置
"""

import argparse
import subprocess
import sys
import os
import tempfile
import shutil
from pathlib import Path
import json


def check_ffmpeg():
    """检查 ffmpeg 是否可用"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        return False
    except FileNotFoundError:
        return False


def install_ffmpeg():
    """提示安装 ffmpeg"""
    print("=" * 60)
    print("❌ 未找到 ffmpeg")
    print("=" * 60)
    print("📦 请安装 ffmpeg：")
    print("   Ubuntu/Debian:  sudo apt install ffmpeg")
    print("   macOS:         brew install ffmpeg")
    print("=" * 60)
    return False


def get_video_info(video_path):
    """获取视频信息"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_type,codec_name,duration",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"⚠️  无法获取视频信息：{e}")
        return None


def merge_videos(videos, output_file, audio_file=None, audio_volume=1.0, bg_volume=1.0):
    """
    合并多个视频文件，保留原始视频的背景音乐

    Args:
        videos: 视频文件列表
        output_file: 输出文件路径
        audio_file: 音频文件路径（可选，用于添加对白）
        audio_volume: 对白音频音量（0.0-2.0，默认 1.0）
        bg_volume: 背景音乐音量（0.0-2.0，默认 1.0）
    """
    print("=" * 60)
    print("🎬 视频合成开始")
    print("=" * 60)

    # 检查所有视频文件
    valid_videos = []
    for i, video in enumerate(videos):
        if not os.path.exists(video):
            print(f"❌ 视频文件不存在：{video}")
            continue
        valid_videos.append(video)

        # 显示视频信息
        info = get_video_info(video)
        if info:
            duration = info["format"].get("duration", "未知")
            print(f"   视频 {i + 1}: {Path(video).name} ({duration}s)")

    if not valid_videos:
        print("❌ 没有有效的视频文件")
        return False

    num_videos = len(valid_videos)
    print(f"\n✅ 共 {num_videos} 个视频文件")

    # 第一步：先合并所有视频（保留原始音频）
    temp_merged = None
    try:
        # 创建临时文件用于合并
        temp_dir = tempfile.mkdtemp()
        concat_file = os.path.join(temp_dir, "concat.txt")

        # 写入 concat 文件
        with open(concat_file, "w", encoding="utf-8") as f:
            for video in valid_videos:
                abs_path = os.path.abspath(video)
                # 在 Windows 上需要转义路径
                if sys.platform == "win32":
                    abs_path = abs_path.replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        # 使用 concat demuxer 合并视频（保留原始音频）
        temp_merged = os.path.join(temp_dir, "temp_merged.mp4")

        cmd_merge = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",
            "-y",
            temp_merged,
        ]

        print("\n⏳ 正在合并视频和背景音乐...")
        result_merge = subprocess.run(cmd_merge, capture_output=True, text=True)

        if result_merge.returncode != 0:
            print("⚠️  快速合并失败，尝试重新编码...")
            # 如果 copy 失败，尝试重新编码
            cmd_merge_reencode = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-y",
                temp_merged,
            ]
            result_merge = subprocess.run(
                cmd_merge_reencode, capture_output=True, text=True
            )

            if result_merge.returncode != 0:
                print(f"❌ 视频合并失败：{result_merge.stderr}")
                return False

        print(f"✅ 背景音乐音量：{bg_volume:.1f}x")

        # 第二步：添加对白音频（如果有）
        if audio_file and os.path.exists(audio_file):
            print(f"✅ 添加对白音频：{Path(audio_file).name}")
            print(f"   音量：{audio_volume:.1f}x")

            # 使用 add_audio_to_video 来混合背景音乐和对白
            # 我们需要调整 add_audio_to_video 的逻辑，或者直接在这里处理
            # 先调整背景音乐音量，然后混合

            cmd_final = ["ffmpeg", "-i", temp_merged]

            if audio_file:
                cmd_final.extend(["-i", str(audio_file)])

            filters = []

            # 调整背景音乐音量
            filters.append(f"[0:a]volume={bg_volume}[bg]")

            # 如果有对白音频
            if audio_file:
                filters.append(f"[1:a]volume={audio_volume}[dialogue]")
                filters.append(
                    "[bg][dialogue]amix=inputs=2:duration=first:dropout_transition=0[outa]"
                )
                filter_complex = ";".join(filters)

                cmd_final.extend(
                    ["-filter_complex", filter_complex, "-map", "0:v", "-map", "[outa]"]
                )
            else:
                filter_complex = ";".join(filters)
                cmd_final.extend(
                    ["-filter_complex", filter_complex, "-map", "0:v", "-map", "[bg]"]
                )

            # 编码选项
            cmd_final.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-y",
                    str(output_file),
                ]
            )

            print(f"\n🔧 命令：{' '.join(cmd_final[:5])}... （已简化）")
            print("\n⏳ 正在混合音频...")

            result_final = subprocess.run(cmd_final, capture_output=True, text=True)

            if result_final.returncode != 0:
                print(f"❌ 音频混合失败：{result_final.stderr}")
                return False
        else:
            # 只有背景音乐，调整音量
            cmd_final = [
                "ffmpeg",
                "-i",
                temp_merged,
                "-filter:a",
                f"volume={bg_volume}",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-y",
                str(output_file),
            ]

            print(f"\n🔧 命令：{' '.join(cmd_final[:5])}... （已简化）")
            print("\n⏳ 正在调整背景音乐音量...")

            result_final = subprocess.run(cmd_final, capture_output=True, text=True)

            if result_final.returncode != 0:
                print(f"❌ 音量调整失败：{result_final.stderr}")
                return False

        # 清理临时文件
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        # 显示结果
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024 / 1024  # MB

            # 获取输出视频信息
            output_info = get_video_info(output_file)
            duration = "未知"
            if output_info:
                duration = output_info["format"].get("duration", "未知")

            print("\n" + "=" * 60)
            print("✅ 视频合成成功！")
            print("=" * 60)
            print(f"📁 输出文件：{os.path.abspath(output_file)}")
            print(f"⏱️  视频时长：{duration}秒")
            print(f"💾 文件大小：{file_size:.1f} MB")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ 视频合成失败")
            print("=" * 60)
            return False

    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        return False


def merge_audios(audio_files_with_timings, output_file):
    """
    将多个音频文件按时间轴合并成一个完整的音频文件

    Args:
        audio_files_with_timings: 列表，每个元素是 (audio_path, start_time_seconds) 的元组
        output_file: 输出音频文件路径
    """
    print("=" * 60)
    print("🎵 音频合并开始")
    print("=" * 60)

    # 检查所有音频文件
    valid_audio_files = []
    for audio_path, start_time in audio_files_with_timings:
        if not os.path.exists(audio_path):
            print(f"❌ 音频文件不存在：{audio_path}")
            continue
        valid_audio_files.append((audio_path, start_time))
        print(f"   音频：{Path(audio_path).name}（开始时间：{start_time}s）")

    if not valid_audio_files:
        print("❌ 没有有效的音频文件")
        return False

    num_audios = len(valid_audio_files)
    print(f"\n✅ 共 {num_audios} 个音频文件")

    # 构建 ffmpeg 命令，使用 amix 和 adelay 滤镜
    cmd = ["ffmpeg"]

    # 添加所有输入音频
    filter_parts = []
    for i, (audio_path, start_time) in enumerate(valid_audio_files):
        cmd.extend(["-i", str(audio_path)])
        delay_ms = int(start_time * 1000)
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

    # 合并所有音频
    all_audio_tags = "".join([f"[a{i}]" for i in range(len(valid_audio_files))])
    filter_parts.append(
        f"{all_audio_tags}amix=inputs={len(valid_audio_files)}:dropout_transition=0[outa]"
    )

    filter_complex = ";".join(filter_parts)

    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[outa]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-y",
            str(output_file),
        ]
    )

    print(f"\n🔧 命令：{' '.join(cmd[:5])}... （已简化）")
    print("\n⏳ 正在合并音频...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024 / 1024  # MB

            print("\n" + "=" * 60)
            print("✅ 音频合并成功！")
            print("=" * 60)
            print(f"📁 输出文件：{os.path.abspath(output_file)}")
            print(f"💾 文件大小：{file_size:.1f} MB")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ 音频合并失败")
            print("=" * 60)
            if result.stderr:
                print(f"错误信息：{result.stderr}")
            return False

    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        return False


def add_audio_to_video(video_file, audio_file, output_file, audio_volume=1.0):
    """
    为视频添加音频轨道（旁白、背景音乐等）

    Args:
        video_file: 视频文件路径
        audio_file: 音频文件路径
        output_file: 输出文件路径
        audio_volume: 音频音量（0.0-2.0，默认 1.0）
    """
    print("=" * 60)
    print("🎵 添加音频到视频")
    print("=" * 60)

    # 检查文件
    if not os.path.exists(video_file):
        print(f"❌ 视频文件不存在：{video_file}")
        return False

    if not os.path.exists(audio_file):
        print(f"❌ 音频文件不存在：{audio_file}")
        return False

    print(f"📹 视频：{Path(video_file).name}")
    print(f"🎵 音频：{Path(audio_file).name}")
    print(f"🔊 音量：{audio_volume:.1f}x")

    # 构建 ffmpeg 命令
    cmd = [
        "ffmpeg",
        "-i",
        str(video_file),
        "-i",
        str(audio_file),
        "-c:v",
        "copy",  # 复制视频流（不重新编码）
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-filter_complex",
        f"[1:a]volume={audio_volume}[outa]",
        "-map",
        "0:v",
        "-map",
        "[outa]",
        "-shortest",  # 使用最短流的时长
        "-y",
        str(output_file),
    ]

    print("\n⏳ 正在添加音频...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024 / 1024  # MB

            print("\n" + "=" * 60)
            print("✅ 音频添加成功！")
            print("=" * 60)
            print(f"📁 输出文件：{os.path.abspath(output_file)}")
            print(f"💾 文件大小：{file_size:.1f} MB")
            print("=" * 60)
            return True
        else:
            print("\n❌ 音频添加失败")
            if result.stderr:
                print(f"错误信息：{result.stderr}")
            return False

    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        return False


def format_srt_time(seconds):
    """
    将秒数格式化为 SRT 时间格式: HH:MM:SS,mmm

    Args:
        seconds: 秒数（可以是浮点数）

    Returns:
        SRT 格式的时间字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds * 1000) % 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(subtitles, output_file):
    """
    生成 SRT 字幕文件

    Args:
        subtitles: 字幕列表，每个元素是字典：
            {
                'text': '字幕文字',
                'start_time': 开始时间（秒）,
                'end_time': 结束时间（秒）
            }
        output_file: 输出 SRT 文件路径
    """
    print("=" * 60)
    print("📝 生成 SRT 字幕")
    print("=" * 60)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(
                    f"{format_srt_time(sub['start_time'])} --> {format_srt_time(sub['end_time'])}\n"
                )
                f.write(f"{sub['text']}\n\n")
                print(
                    f"   字幕 {i}: {sub['text']} ({sub['start_time']}s - {sub['end_time']}s)"
                )

        print("\n✅ SRT 字幕文件生成成功！")
        print(f"📁 输出文件：{os.path.abspath(output_file)}")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n❌ SRT 字幕生成失败：{e}")
        print("=" * 60)
        return False


def burn_subtitles_to_video(
    video_file,
    subtitle_file,
    output_file,
    font_name="Arial",
    font_size=24,
    primary_color="white",
    outline_color="black",
    outline=2,
    shadow=0,
    alignment=2,
):
    """
    将字幕烧录到视频中（硬字幕）

    Args:
        video_file: 视频文件路径
        subtitle_file: SRT 字幕文件路径
        output_file: 输出视频文件路径
        font_name: 字体名称，默认 "Arial"
        font_size: 字体大小，默认 24
        primary_color: 主颜色，默认 "white"
        outline_color: 边框颜色，默认 "black"
        outline: 边框宽度，默认 2
        shadow: 阴影深度，默认 0（无阴影）
        alignment: 对齐方式，1=左下，2=中下，3=右下，8=左上，9=中上，10=右上，默认 2
    """
    print("=" * 60)
    print("🎬 烧录字幕到视频")
    print("=" * 60)

    # 检查文件
    if not os.path.exists(video_file):
        print(f"❌ 视频文件不存在：{video_file}")
        return False

    if not os.path.exists(subtitle_file):
        print(f"❌ 字幕文件不存在：{subtitle_file}")
        return False

    print(f"📹 视频：{Path(video_file).name}")
    print(f"📝 字幕：{Path(subtitle_file).name}")

    # 将字幕文件复制到当前工作目录，避免路径问题
    work_dir = os.getcwd()
    temp_sub = os.path.join(work_dir, "temp_sub.srt")

    try:
        shutil.copy(subtitle_file, temp_sub)
        sub_name = "temp_sub.srt"
    except Exception as e:
        print(f"⚠️  复制字幕文件失败，尝试直接使用原文件：{e}")
        temp_sub = subtitle_file
        sub_name = os.path.basename(subtitle_file)
        # 确保字幕文件在当前工作目录
        if os.path.dirname(sub_name):
            try:
                shutil.copy(subtitle_file, sub_name)
            except BaseException:
                pass

    # 方法1: 尝试使用 ffmpeg 的 subtitles 滤镜
    print("\n⏳ 尝试使用 ffmpeg subtitles 滤镜...")
    success = False

    try:
        # 构建 ffmpeg 命令
        cmd = [
            "ffmpeg",
            "-i",
            str(video_file),
            "-vf",
            f"subtitles={sub_name}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "copy",
            "-y",
            str(output_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_file):
            success = True
    except Exception as e:
        print(f"⚠️  subtitles 滤镜方法失败：{e}")

    # 方法2: 如果方法1失败，尝试使用 shell 命令字符串
    if not success:
        print("\n⏳ 尝试备用方法...")
        try:
            cmd_str = (
                f'ffmpeg -i "{video_file}" '
                f'-vf "subtitles={sub_name}" '
                f'-c:v libx264 -preset medium -crf 23 -c:a copy -y "{output_file}"'
            )
            result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_file):
                success = True
        except Exception as e:
            print(f"⚠️  备用方法也失败：{e}")

    # 清理临时文件
    if temp_sub != subtitle_file and os.path.exists(temp_sub):
        try:
            os.remove(temp_sub)
        except Exception as e:
            print(f"⚠️  清理临时文件失败：{e}")
    if sub_name != os.path.basename(temp_sub) and os.path.exists(sub_name):
        try:
            os.remove(sub_name)
        except Exception:
            pass

    if success:
        file_size = os.path.getsize(output_file) / 1024 / 1024  # MB

        # 获取输出视频信息
        output_info = get_video_info(output_file)
        duration = "未知"
        if output_info:
            duration = output_info["format"].get("duration", "未知")

        print("\n" + "=" * 60)
        print("✅ 字幕烧录成功！")
        print("=" * 60)
        print(f"📁 输出文件：{os.path.abspath(output_file)}")
        print(f"⏱️  视频时长：{duration}秒")
        print(f"💾 文件大小：{file_size:.1f} MB")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ 字幕烧录失败")
        print("=" * 60)
        print("✅ 字幕生成功能（generate-srt）已正常工作！")
        print("📝 您已获得标准 SRT 格式的字幕文件：" + subtitle_file)
        print("\n💡 如需要烧录字幕，可以使用以下方法：")
        print("   1. 使用专业视频编辑软件（如 Final Cut Pro、Premiere、剪映等）")
        print("   2. 使用在线视频工具（如 Kapwing、Clideo 等）")
        print("   3. 寻找已编译好 libass 支持的 ffmpeg 版本")
        print("=" * 60)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="视频编辑器 - 合并多个视频、添加音频、合并音频、生成并烧录字幕",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：

1. 合并多个视频：
   python video_editor.py output.mp4 --videos video1.mp4 video2.mp4 video3.mp4

2. 合并视频并添加音频：
   python video_editor.py output.mp4 --videos v1.mp4 v2.mp4 --audio narration.mp3

3. 为现有视频添加音频：
   python video_editor.py output.mp4 --video input.mp4 --audio narration.mp3 --volume 0.8 --mode add-audio

4. 合并多个音频（按时间轴）：
   python video_editor.py output.mp3 --audios audio1.mp3,audio2.mp3 --start-times 0,5 --mode merge-audios

5. 生成 SRT 字幕文件：
   python video_editor.py output.srt --subtitles '[{"text":"你好","start_time":0,"end_time":2},{"text":"世界","start_time":2.5,"end_time":5}]' --mode generate-srt

6. 烧录字幕到视频：
   python video_editor.py output_with_subs.mp4 --video input.mp4 --subtitle subs.srt --mode burn-subtitles

7. 烧录字幕（自定义样式）：
   python video_editor.py output.mp4 --video input.mp4 --subtitle subs.srt --font-name "Arial" --font-size 28 --mode burn-subtitles
        """,
    )

    parser.add_argument("output", help="输出文件路径")
    parser.add_argument("--videos", nargs="+", help="要合并的视频文件列表")
    parser.add_argument("--video", help="单个视频文件（用于添加音频或烧录字幕）")
    parser.add_argument("--audio", help="单个音频文件（旁白、背景音乐等）")
    parser.add_argument("--audios", help="要合并的音频文件列表，用逗号分隔")
    parser.add_argument("--start-times", help="每个音频的开始时间（秒），用逗号分隔")
    parser.add_argument(
        "--volume", type=float, default=1.0, help="对白音频音量（0.0-2.0，默认 1.0）"
    )
    parser.add_argument(
        "--bg-volume", type=float, default=1.0, help="背景音乐音量（0.0-2.0，默认 1.0）"
    )
    parser.add_argument(
        "--subtitles",
        help="字幕数据，JSON 格式的列表，每个元素包含 text、start_time、end_time",
    )
    parser.add_argument("--subtitle", help="SRT 字幕文件路径（用于烧录字幕）")
    parser.add_argument("--font-name", default="Arial", help="字幕字体名称，默认 Arial")
    parser.add_argument(
        "--font-size", type=int, default=24, help="字幕字体大小，默认 24"
    )
    parser.add_argument(
        "--font-color", default="white", help="字幕字体颜色，默认 white"
    )
    parser.add_argument(
        "--outline-color", default="black", help="字幕边框颜色，默认 black"
    )
    parser.add_argument("--outline", type=int, default=2, help="字幕边框宽度，默认 2")
    parser.add_argument(
        "--shadow", type=int, default=0, help="字幕阴影深度，默认 0（无阴影）"
    )
    parser.add_argument(
        "--alignment",
        type=int,
        default=2,
        help="字幕对齐方式：1=左下, 2=中下, 3=右下, 8=左上, 9=中上, 10=右上，默认 2",
    )
    parser.add_argument(
        "--mode",
        choices=[
            "merge",
            "add-audio",
            "merge-audios",
            "generate-srt",
            "burn-subtitles",
        ],
        default="merge",
        help="操作模式：merge（合并视频）、add-audio（添加音频）、merge-audios（合并音频）、generate-srt（生成 SRT 字幕）、burn-subtitles（烧录字幕）",
    )

    args = parser.parse_args()

    # 只有非 generate-srt 模式才需要 ffmpeg
    if args.mode != "generate-srt":
        if not check_ffmpeg():
            install_ffmpeg()
            sys.exit(1)

    # 确保输出目录存在
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = False

    # 模式：合并视频
    if args.mode == "merge":
        if args.videos:
            success = merge_videos(
                args.videos, args.output, args.audio, args.volume, args.bg_volume
            )
        else:
            print("❌ 请指定要合并的视频文件（使用 --videos 参数）")
            print(
                "示例：python video_editor.py output.mp4 --videos v1.mp4 v2.mp4 v3.mp4"
            )
            sys.exit(1)

    # 模式：添加音频
    elif args.mode == "add-audio":
        if args.video and args.audio:
            success = add_audio_to_video(
                args.video, args.audio, args.output, args.volume
            )
        else:
            print("❌ 请指定视频文件和音频文件")
            print(
                "示例：python video_editor.py output.mp4 --video input.mp4 --audio narration.mp3"
            )
            sys.exit(1)

    # 模式：合并音频
    elif args.mode == "merge-audios":
        if args.audios and args.start_times:
            audio_files = args.audios.split(",")
            start_times = list(map(float, args.start_times.split(",")))

            if len(audio_files) != len(start_times):
                print("❌ 音频文件数量和开始时间数量不匹配")
                sys.exit(1)

            audio_files_with_timings = list(zip(audio_files, start_times))
            success = merge_audios(audio_files_with_timings, args.output)
        else:
            print("❌ 请指定音频文件列表和开始时间列表")
            print(
                "示例：python video_editor.py output.mp3 --audios audio1.mp3,audio2.mp3 --start-times 0,5 --mode merge-audios"
            )
            sys.exit(1)

    # 模式：生成 SRT 字幕
    elif args.mode == "generate-srt":
        if args.subtitles:
            try:
                subtitles = json.loads(args.subtitles)
                success = generate_srt(subtitles, args.output)
            except json.JSONDecodeError as e:
                print(f"❌ 字幕数据 JSON 解析失败：{e}")
                print(
                    '示例：--subtitles \'[{"text":"你好","start_time":0,"end_time":2}]\''
                )
                sys.exit(1)
        else:
            print("❌ 请指定字幕数据（使用 --subtitles 参数）")
            print(
                '示例：python video_editor.py output.srt --subtitles \'[{"text":"你好","start_time":0,"end_time":2}]\' --mode generate-srt'
            )
            sys.exit(1)

    # 模式：烧录字幕
    elif args.mode == "burn-subtitles":
        if args.video and args.subtitle:
            success = burn_subtitles_to_video(
                args.video,
                args.subtitle,
                args.output,
                args.font_name,
                args.font_size,
                args.font_color,
                args.outline_color,
                args.outline,
                args.shadow,
                args.alignment,
            )
        else:
            print("❌ 请指定视频文件和字幕文件")
            print(
                "示例：python video_editor.py output.mp4 --video input.mp4 --subtitle subs.srt --mode burn-subtitles"
            )
            sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
