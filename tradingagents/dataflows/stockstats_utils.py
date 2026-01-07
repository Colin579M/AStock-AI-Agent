import pandas as pd
import yfinance as yf
from stockstats import wrap
from typing import Annotated
import os
from .config import get_config


def _clean_yfinance_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    清理 yfinance 下载的数据，移除无效行

    yfinance 有时会在数据末尾添加垃圾数据（如 "1,0"），
    这会导致日期解析失败。
    """
    if data.empty:
        return data

    # 确保 Date 列存在
    if "Date" not in data.columns:
        return data

    # 转换 Date 列为 datetime，无效值设为 NaT
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    # 移除 Date 为 NaT 的行（无效日期）
    data = data.dropna(subset=["Date"])

    # 移除重复日期，保留第一个
    data = data.drop_duplicates(subset=["Date"], keep="first")

    # 按日期排序
    data = data.sort_values("Date").reset_index(drop=True)

    return data


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
        data_dir: Annotated[
            str,
            "directory where the stock data is stored.",
        ],
        online: Annotated[
            bool,
            "whether to use online tools to fetch data or offline tools. If True, will use online tools.",
        ] = False,
    ):
        df = None
        data = None

        if not online:
            try:
                data = pd.read_csv(
                    os.path.join(
                        data_dir,
                        f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                    )
                )
                # 清理离线数据中的无效行
                data = _clean_yfinance_data(data)
                df = wrap(data)
            except FileNotFoundError:
                raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
        else:
            # Get today's date as YYYY-mm-dd to add to cache
            today_date = pd.Timestamp.today()
            curr_date = pd.to_datetime(curr_date)

            end_date = today_date
            start_date = today_date - pd.DateOffset(years=15)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")

            # Get config and ensure cache directory exists
            config = get_config()
            os.makedirs(config["data_cache_dir"], exist_ok=True)

            data_file = os.path.join(
                config["data_cache_dir"],
                f"{symbol}-YFin-data-{start_date}-{end_date}.csv",
            )

            if os.path.exists(data_file):
                data = pd.read_csv(data_file)
                # 清理缓存数据中的无效行
                data = _clean_yfinance_data(data)
            else:
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    multi_level_index=False,
                    progress=False,
                    auto_adjust=True,
                )
                data = data.reset_index()
                # 清理下载数据中的无效行
                data = _clean_yfinance_data(data)
                # 保存清理后的数据
                data.to_csv(data_file, index=False)

            df = wrap(data)
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            curr_date = curr_date.strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
