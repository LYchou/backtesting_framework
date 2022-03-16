from typing import Iterator
import pandas as pd
from datetime import datetime
from . import strategy
from . import data_center
from . import analysis

class Cerebro:
    '''
    大腦控制資料輸入、策略輸入、初始化把資料傳給 data_center
    '''

    def __init__(self):
        self.datas_table = pd.DataFrame()
        self.ticker_dict = dict()
        self.cash = 100000
        self.notify_orNot = False
        self.start_date = None  # 所有資料計算的範圍
        self.end_date = None    # 所有資料計算的範圍
        self.strategy_execute_start_date = None   # 執行策略的時間，真的開始迭代執行 strategy.next()
        self.dateList = None
        self.strategy_obj = strategy.Strategy() #　初始化 之後用addstrategy可以覆蓋
        self.close_at_BacktestingEndDate_orNot = True # 判斷是否要再回測最後一天平倉

    
    ### 控制回測主要方法順序 ###

    def run(self):
        # 重新設定參數
        self.__reset_params()
        self.analysis_obj = analysis.Analysis(self.data_center)

        # 以下可以程式碼可以呼叫 data center (self.datat_center已經準備好)
        self.strategy_obj.initial()

        # 迭代每個交易日
        for date in self.dateList:

            if date<self.strategy_execute_start_date:
                # 策略還沒開始
                self.strategy_obj.save_AccountState()
                self.strategy_obj.set_date_forward()
                # 以下不執行，進入下個迴圈
                continue


            self.strategy_obj.update_AccountState()
            self.strategy_obj.save_AccountState()

            # 執行動作
            self.strategy_obj.pre_next()
            self.strategy_obj.next()

            # 如果持有的order明天是他價格的最後一天，今天掛上賣單
            # 注意LastTradingDay定義會因 self.close_at_BacktestingEndDate_orNot的直有所不同
            # 詳見:order_obj.check_today_is_LastTradingDay_orNot()之說明文字
            self.strategy_obj.close_orders_AtTheirLastTradingDay()

            self.strategy_obj.after_next()

            
            if self.data_center.date!=self.dateList[-1]:
                # 非最後一天，可以往後迭代交易
                ########### tomorrow ###########
                self.strategy_obj.set_date_forward()
                self.strategy_obj.pre_open()
                self.strategy_obj.trading()

                

        # 回測結束
        self.strategy_obj.update_AccountState()
        self.strategy_obj.stop()
        self.analysis_obj.get_orders_InfoTable()
        self.analysis_obj.get_account_timeseries_state()

    def __select_dateList(self):
        '''
        根據起始和結束日期找到區間內的所有交易日
        '''
        dateList = list(self.datas_table.index)
        if dateList==[]:
            return
        else:
            # 計算 如果沒有輸入回測起始和結束日期，預設資料最早與最晚。
            self.start_date = self.datas_table.index.min() if not self.start_date else self.start_date
            self.end_date = self.datas_table.index.max() if not self.end_date else self.end_date
            #
            self.dateList = [date for date in dateList if (date<=self.end_date)and(date>=self.start_date)]
            # 再設定一次的原因是原本設定的起始結束日期可能非交易日，日期不會在資料中
            self.start_date = self.dateList[0]
            self.end_date = self.dateList[-1]

    def __process_datas_table(self):
        if len(self.datas_table)>0:
            # 如果self.datas_table有資料，以此為主覆蓋self.ticker_dict
            self.ticker_dict = {
                ticker:self.datas_table[ticker][['HIGH', 'CLOSE', 'LOW', 'OPEN', 'VOLUME']] for ticker in self.datas_table.columns.levels[0]
                }
        else:
            # 如果self.datas_table沒有資料，以self.ticker_dict生成self.datas_table
            self.__setup_DatasTable_by_TickerDict()

    def __packge_AllData(self):
        self.data_center = data_center.Data_center(
            ticker_dict=self.ticker_dict,
            dateList=self.dateList,
            start_date=self.start_date,
            end_date=self.end_date,
            strategy_execute_start_date = self.strategy_execute_start_date,
            value=self.value,
            cash=self.cash,
            notify_orNot = self.notify_orNot,
            close_at_BacktestingEndDate_orNot = self.close_at_BacktestingEndDate_orNot
        )

    def __reset_params(self):
        '''
        在 call self.run() 前，
        先把參數設定好，並且傳給 strategy_obj
        '''
        self.value = self.cash 
        self.__process_datas_table()
        self.__select_dateList()
        self.strategy_execute_start_date = self.strategy_execute_start_date if self.strategy_execute_start_date else self.dateList[0]
        self.__packge_AllData()

        self.strategy_obj.setup_data_center(self.data_center)  # 把當前建立好的date_center傳進去傳給strategy_obj

    def addstrategy(self, strategy_method, **params):
        '''
        把策略傳給 cerebro，同時可以設定param給strategy_obj
        '''
        self.strategy_obj = strategy_method(**params)



    def __setup_DatasTable_by_TickerDict(self):
        temp_ticker_dict = dict()
        for ticker in self.ticker_dict:
            df = self.ticker_dict[ticker]
            columns_tuples = [(ticker, col) for col in df.columns]
            df.columns = pd.MultiIndex.from_tuples(columns_tuples)
            temp_ticker_dict[ticker] = df

        from functools import reduce
        self.datas_table = reduce(
                            lambda df1,df2: df1.merge(df2, left_index=True, right_index=True, how='outer'),
                            temp_ticker_dict.values()
                            )
        # 把MultiIndex恢復
        self.ticker_dict = {
                ticker:self.datas_table[ticker][['HIGH', 'CLOSE', 'LOW', 'OPEN', 'VOLUME']] for ticker in self.datas_table.columns.levels[0]
                }


