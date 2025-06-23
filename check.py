# -*- coding: utf-8 -*-
import mysql.connector
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# --- 可配置区域 ---

# 1. 数据库连接信息
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "new-api",
}

# 2. 错误率统计时要忽略的错误内容关键字
IGNORED_ERROR_PATTERNS = [
    "the maximum number of tokens",
    "user quota is not enough",
]


# --- 辅助函数 ---


def get_display_width(s):
    """计算字符串的显示宽度，中文字符计为2，英文字符计为1"""
    width = 0
    for char in str(s):  # 确保输入是字符串
        if "\u4e00" <= char <= "\u9fff":
            width += 2
        else:
            width += 1
    return width


def format_tokens_to_million(tokens):
    """将token数量格式化为百万单位（m），保留两位小数"""
    if not isinstance(tokens, (int, float, Decimal)):
        return "0.00m"
    return f"{float(tokens) / 1_000_000:.2f}m"


def parse_time_string(time_str):
    """
    解析多种格式的时间字符串，返回 datetime 对象。
    支持格式: Y-m-d H:M:S, Y-m-d H:M, Y-m-d, H:M, m-d H:M
    """
    now = datetime.now()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%H:%M",
        "%H:%M:%S",
        "%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            if fmt in ["%H:%M", "%H:%M:%S"]:
                dt = datetime.strptime(time_str, fmt)
                return now.replace(
                    hour=dt.hour, minute=dt.minute, second=dt.second, microsecond=0
                )
            if fmt == "%m-%d %H:%M":
                dt = datetime.strptime(time_str, fmt)
                return dt.replace(year=now.year)
            dt = datetime.strptime(time_str, fmt)
            return dt
        except ValueError:
            continue
    return None


# --- 脚本核心功能 ---


def get_db_connection():
    """根据 DB_CONFIG 建立并返回数据库连接"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None


def get_user_stats(cursor, where_clause, params):
    """获取用户统计数据"""
    print("\n" + "=" * 36 + " 用户统计 " + "=" * 36)
    query_user = f"""
        SELECT
            l.user_id,
            l.username,
            COUNT(l.id) as request_count,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens
        FROM logs l
        {where_clause}
        GROUP BY l.user_id, l.username
        ORDER BY request_count DESC
        LIMIT 5
    """
    cursor.execute(query_user, params)
    user_stats = cursor.fetchall()

    col_user_name_width = 42
    col_user_req_width = 20
    col_user_tokens_width = 20

    header_user_name = "用户名(ID)"
    header_user_req = "请求次数"
    header_user_tokens = "消耗Tokens"
    print(
        f"{header_user_name}{' ' * (col_user_name_width - get_display_width(header_user_name))}"
        f"{header_user_req}{' ' * (col_user_req_width - get_display_width(header_user_req))}"
        f"{header_user_tokens}"
    )
    print("-" * (col_user_name_width + col_user_req_width + col_user_tokens_width))

    for row in user_stats:
        user_display = f"{row['username']}({row['user_id']})"
        req_count = str(row["request_count"])
        tokens_val = format_tokens_to_million(row["total_tokens"])
        print(
            f"{user_display}{' ' * (col_user_name_width - get_display_width(user_display))}"
            f"{req_count}{' ' * (col_user_req_width - get_display_width(req_count))}"
            f"{tokens_val}"
        )


def get_token_stats(cursor, where_clause, params):
    """获取Token统计数据"""
    print("\n" + "=" * 36 + " Token统计 " + "=" * 35)
    final_params = list(params)
    final_where_clause = where_clause + " AND l.token_name != ''"

    query_token = f"""
        SELECT
            l.token_id,
            l.token_name,
            COUNT(l.id) as request_count,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens
        FROM logs l
        {final_where_clause}
        GROUP BY l.token_id, l.token_name
        ORDER BY request_count DESC
        LIMIT 5
    """
    cursor.execute(query_token, final_params)
    token_stats = cursor.fetchall()

    col_token_name_width = 42
    col_token_req_width = 20
    col_token_tokens_width = 20

    header_token_name = "Token名称(ID)"
    header_token_req = "请求次数"
    header_token_tokens = "消耗Tokens"
    print(
        f"{header_token_name}{' ' * (col_token_name_width - get_display_width(header_token_name))}"
        f"{header_token_req}{' ' * (col_token_req_width - get_display_width(header_token_req))}"
        f"{header_token_tokens}"
    )
    print("-" * (col_token_name_width + col_token_req_width + col_token_tokens_width))

    for row in token_stats:
        token_display = f"{row['token_name']}({row['token_id']})"
        req_count = str(row["request_count"])
        tokens_val = format_tokens_to_million(row["total_tokens"])
        print(
            f"{token_display}{' ' * (col_token_name_width - get_display_width(token_display))}"
            f"{req_count}{' ' * (col_token_req_width - get_display_width(req_count))}"
            f"{tokens_val}"
        )


def get_model_stats(cursor, where_clause, params):
    """获取模型统计数据"""
    print("\n" + "=" * 36 + " 模型统计 " + "=" * 36)
    final_params = list(params)
    final_where_clause = where_clause + " AND l.model_name != ''"

    query_model = f"""
        SELECT
            l.model_name,
            COUNT(l.id) as request_count,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens
        FROM logs l
        {final_where_clause}
        GROUP BY l.model_name
        ORDER BY request_count DESC
        LIMIT 5
    """
    cursor.execute(query_model, final_params)
    model_stats = cursor.fetchall()

    col_model_name_width = 42
    col_req_width = 20
    col_tokens_width = 20

    header_model_name = "模型名称"
    header_req = "请求次数"
    header_tokens = "消耗Tokens"
    print(
        f"{header_model_name}{' ' * (col_model_name_width - get_display_width(header_model_name))}"
        f"{header_req}{' ' * (col_req_width - get_display_width(header_req))}"
        f"{header_tokens}"
    )
    print("-" * (col_model_name_width + col_req_width + col_tokens_width))

    for row in model_stats:
        model_display = row["model_name"]
        req_count = str(row["request_count"])
        tokens_val = format_tokens_to_million(row["total_tokens"])
        print(
            f"{model_display}{' ' * (col_model_name_width - get_display_width(model_display))}"
            f"{req_count}{' ' * (col_req_width - get_display_width(req_count))}"
            f"{tokens_val}"
        )


def get_ip_stats(cursor, where_clause, params):
    """获取IP统计数据"""
    print("\n" + "=" * 37 + " IP统计 " + "=" * 37)
    final_params = list(params)
    final_where_clause = where_clause + " AND l.ip IS NOT NULL AND l.ip != ''"
    query_ip = f"""
        SELECT
            l.ip,
            COUNT(l.id) as request_count,
            COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens
        FROM logs l
        {final_where_clause}
        GROUP BY l.ip
        ORDER BY request_count DESC
        LIMIT 5
    """
    cursor.execute(query_ip, final_params)
    ip_stats = cursor.fetchall()

    col_ip_name_width = 42
    col_req_width = 20
    col_tokens_width = 20

    header_ip_name = "IP地址"
    header_req = "请求次数"
    header_tokens = "消耗Tokens"
    print(
        f"{header_ip_name}{' ' * (col_ip_name_width - get_display_width(header_ip_name))}"
        f"{header_req}{' ' * (col_req_width - get_display_width(header_req))}"
        f"{header_tokens}"
    )
    print("-" * (col_ip_name_width + col_req_width + col_tokens_width))

    for row in ip_stats:
        ip_display = row["ip"]
        req_count = str(row["request_count"])
        tokens_val = format_tokens_to_million(row["total_tokens"])
        print(
            f"{ip_display}{' ' * (col_ip_name_width - get_display_width(ip_display))}"
            f"{req_count}{' ' * (col_req_width - get_display_width(req_count))}"
            f"{tokens_val}"
        )


def generate_report(cli_args=None):
    """主函数，执行所有统计和报告生成任务"""
    connection = get_db_connection()
    if not connection:
        return

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        where_clause = ""
        params = ()

        # --- 动态生成错误过滤条件 ---
        error_filter_clause = ""
        error_filter_params = []
        if IGNORED_ERROR_PATTERNS:
            for pattern in IGNORED_ERROR_PATTERNS:
                error_filter_clause += " AND l.content NOT LIKE %s"
                error_filter_params.append(f"%{pattern}%")

        print(f"\n报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not cli_args:
            # Default to last 24 hours if no arguments
            hours = 24
            start_time = datetime.now() - timedelta(hours=hours)
            where_clause = "WHERE l.created_at >= %s"
            params = (int(start_time.timestamp()),)
            print(f"查询模式: 默认最近 {hours} 小时")
            print(f"查询时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至今")
        else:
            print("查询模式: 自定义时间范围")
            start_time, end_time = None, None

            # Case 1: Integer for hours
            if len(cli_args) == 1:
                try:
                    hours = int(cli_args[0])
                    if hours <= 0:
                        print("错误: 小时数必须为正整数。")
                        return
                    start_time = datetime.now() - timedelta(hours=hours)
                    where_clause = "WHERE l.created_at >= %s"
                    params = (int(start_time.timestamp()),)
                    print(
                        f"查询时间范围: 最近 {hours} 小时 ({start_time.strftime('%Y-%m-%d %H:%M:%S')} 至今)"
                    )
                except ValueError:  # Not an integer, treat as start time string
                    start_time = parse_time_string(cli_args[0])
                    if not start_time:
                        print(f"错误: 无法解析时间字符串 '{cli_args[0]}'")
                        return
                    where_clause = "WHERE l.created_at >= %s"
                    params = (int(start_time.timestamp()),)
                    print(
                        f"查询时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至今"
                    )

            # Case 2: Two time strings
            elif len(cli_args) == 2:
                start_time = parse_time_string(cli_args[0])
                end_time = parse_time_string(cli_args[1])
                if not start_time or not end_time:
                    if not start_time:
                        print(f"错误: 无法解析开始时间字符串 '{cli_args[0]}'")
                    if not end_time:
                        print(f"错误: 无法解析结束时间字符串 '{cli_args[1]}'")
                    return
                if start_time >= end_time:
                    print("错误: 开始时间必须早于结束时间。")
                    return

                where_clause = "WHERE l.created_at >= %s AND l.created_at <= %s"
                params = (int(start_time.timestamp()), int(end_time.timestamp()))
                print(
                    f"查询时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                print("错误: 参数数量过多。最多支持两个时间范围参数。")
                return

        # --- 生成报告 ---
        print("\n" + "=" * 52 + " 总览 " + "=" * 51)
        query_total = f"""
            SELECT
                COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens,
                COUNT(l.id) as total_requests,
                SUM(CASE WHEN (l.type = 5 OR (l.type = 2 AND l.completion_tokens = 0 AND content LIKE '%超时%')) AND l.content LIKE '%429%'  {error_filter_clause} THEN 1 ELSE 0 END) as error_429_count,
                SUM(CASE WHEN (l.type = 5 OR (l.type = 2 AND l.completion_tokens = 0 AND content LIKE '%超时%')) AND l.content NOT LIKE '%429%'  {error_filter_clause} THEN 1 ELSE 0 END) as normal_error_count
            FROM logs l
            {where_clause}
        """
        final_params_total = error_filter_params + error_filter_params + list(params)
        cursor.execute(query_total, final_params_total)
        total_stats = cursor.fetchone()

        total_req = total_stats["total_requests"]
        error_429 = total_stats["error_429_count"]
        normal_error = total_stats["normal_error_count"]
        p_429 = (
            f"({error_429 / total_req:.1%})"
            if total_req and total_req > 0
            else "(0.0%)"
        )
        p_normal = (
            f"({normal_error / total_req:.1%})"
            if total_req and total_req > 0
            else "(0.0%)"
        )

        print(f"总消耗Tokens: {format_tokens_to_million(total_stats['total_tokens'])}")
        print(f"总请求次数: {total_req} 次")
        print(f"429错误: {error_429} {p_429}")
        print(f"普通错误: {normal_error} {p_normal}")

        print("\n" + "=" * 50 + " 渠道统计 " + "=" * 49)
        query_channel = f"""
            SELECT
                l.channel_id,
                c.name as channel_name,
                COUNT(l.id) as total_requests,
                SUM(CASE WHEN (l.type = 5 OR (l.type = 2 AND l.completion_tokens = 0 AND content LIKE '%超时%')) AND l.content LIKE '%429%'  {error_filter_clause} THEN 1 ELSE 0 END) as error_429_count,
                SUM(CASE WHEN (l.type = 5 OR (l.type = 2 AND l.completion_tokens = 0 AND content LIKE '%超时%')) AND l.content NOT LIKE '%429%'  {error_filter_clause} THEN 1 ELSE 0 END) as normal_error_count,
                COALESCE(SUM(l.prompt_tokens + l.completion_tokens), 0) AS total_tokens
            FROM logs l
            LEFT JOIN channels c ON l.channel_id = c.id
            {where_clause}
            GROUP BY l.channel_id, c.name
            HAVING COUNT(l.id) >= 10
            ORDER BY total_requests DESC
        """
        final_params_channel = error_filter_params + error_filter_params + list(params)
        cursor.execute(query_channel, final_params_channel)
        channel_stats = cursor.fetchall()

        col_channel_name_width = 42
        col_429_width = 20
        col_normal_error_width = 20
        col_total_req_width = 12
        col_tokens_width = 15

        header_channel = "渠道名称(ID)"
        header_429 = "429错误"
        header_normal = "普通错误"
        header_requests = "请求总数"
        header_tokens = "消耗Tokens"
        print(
            f"{header_channel}{' ' * (col_channel_name_width - get_display_width(header_channel))}"
            f"{header_429}{' ' * (col_429_width - get_display_width(header_429))}"
            f"{header_normal}{' ' * (col_normal_error_width - get_display_width(header_normal))}"
            f"{header_requests}{' ' * (col_total_req_width - get_display_width(header_requests))}"
            f"{header_tokens}"
        )
        print(
            "-"
            * (
                col_channel_name_width
                + col_429_width
                + col_normal_error_width
                + col_total_req_width
                + col_tokens_width
            )
        )

        for row in channel_stats:
            channel_id = row.get("channel_id", "N/A")
            channel_name_raw = row.get("channel_name") or "未知渠道"
            channel_name = f"{channel_name_raw}({channel_id})"
            total_req = row["total_requests"]
            error_429 = row["error_429_count"]
            normal_error = row["normal_error_count"]
            p_429 = f"({error_429 / total_req:.1%})" if total_req > 0 else "(0.0%)"
            p_normal = (
                f"({normal_error / total_req:.1%})" if total_req > 0 else "(0.0%)"
            )
            col1_val = channel_name
            col2_val = f"{error_429} {p_429}"
            col3_val = f"{normal_error} {p_normal}"
            col4_val = str(total_req)
            col5_val = format_tokens_to_million(row["total_tokens"])
            print(
                f"{col1_val}{' ' * (col_channel_name_width - get_display_width(col1_val))}"
                f"{col2_val}{' ' * (col_429_width - get_display_width(col2_val))}"
                f"{col3_val}{' ' * (col_normal_error_width - get_display_width(col3_val))}"
                f"{col4_val}{' ' * (col_total_req_width - get_display_width(col4_val))}"
                f"{col5_val}"
            )

        get_user_stats(cursor, where_clause, params)
        get_token_stats(cursor, where_clause, params)
        get_model_stats(cursor, where_clause, params)
        get_ip_stats(cursor, where_clause, params)

    except mysql.connector.Error as err:
        print(f"报告生成过程中发生数据库错误: {err}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    finally:
        if connection and connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()


if __name__ == "__main__":
    generate_report(cli_args=sys.argv[1:])
