from common import *
from config import *
from datetime import datetime
import MetaTrader5 as mt5
# import pandas as pd
import pytz
import pandas as pd

# base_data_api = BaseDataApi(api_key=api_key, hid=hid, all_data_path=all_data_path,
#                             strategy_result_path=strategy_result_path)

start_time = datetime.now()
# ===================  记录日志  ===================
record_log(f' -->开始更新数据', send=True)
# ===================  记录日志  ===================

# 建立与MetaTrader 5程序端的连接
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()
# 将时区设置为UTC
timezone = pytz.timezone("Etc/UTC")
# 以UTC时区创建'datetime'对象，以避免实现本地时区偏移
time_back = datetime.now()
# symbol_name = 'USOILm'
symbol_name_list = ['XAUUSDm', 'USOILm']
# utc_from = datetime(time_back.year, time_back.month,time_back.day,time_back.hour, time_back.minute,tzinfo=timezone)
list_symbol_time = [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H2, mt5.TIMEFRAME_H4, ]


def down_lode():
    for symbol_name in symbol_name_list:
        for symbol_time in list_symbol_time:
            print(symbol_time, str(symbol_time)[6:])
            rates = mt5.copy_rates_from(symbol_name, symbol_time, time_back, 99999)
            # # rates = mt5.copy_rates_from_pos('XAUUSDm', mt5.TIMEFRAME_D1, 0, 10)
            # print(rates)
            # # for rate in rates:
            # #     print(rate)
            #
            # # 从所获得的数据创建DataFrame
            rates_frame = pd.DataFrame(rates)
            # 将时间（以秒为单位）转换为日期时间格式
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
            rates_frame['SECUCODE'] = symbol_name
            # rates_frame['SECURITY_NAME_ABBR'] = '石油_美元'
            rename_dict = {'SECUCODE': '股票代码', 'time': '交易日期',
                           'open': '开盘价', 'high': '最高价', 'low': '最低价',
                           'close': '收盘价', 'tick_volume': '成交量', 'spread': '点差'
                           }
            rates_frame.rename(columns=rename_dict, inplace=True)
            # rates_frame['时间差'] = rates_frame['交易日期'].apply(lambda x: x.hour)
            rates_frame['时间差'] = rates_frame['交易日期'] - rates_frame['交易日期'].shift()
            range_time = rates_frame['交易日期'].iloc[-1] - rates_frame['交易日期'].iloc[-2]
            rates_frame['时间差'] = rates_frame['时间差'] - range_time
            # #
            #
            rates_frame.dropna(inplace=True)
            # # rates_frame['时间差'] = rates_frame['时间差'].apply(lambda x: x.hour)
            rates_frame['时间差'] = rates_frame['时间差'].apply(lambda x: x / pd.Timedelta(1, 'h'))
            rates_frame = rates_frame[rates_frame['时间差'] == 0.0]
            rates_frame.to_csv('F:/use_code/MTA5/'f'{symbol_name}' + f'{symbol_time}' + '.csv', encoding='gbk',
                               index=False)
            # # 显示数据
            print("\nDisplay dataframe with data")
            print(rates_frame)


if __name__ == '__main__':
    # python_exe = sys.executable
    down_lode()
    mt5.shutdown()
    # os.system('%s 13dzjy_Q1.py' % python_exe)
    # os.system('%s 14dzjy_everyday.py' % python_exe)
