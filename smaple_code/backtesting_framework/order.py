import numpy as np
import datetime

class Order:
    '''
    self.executed_date 為這個 order 開倉的狀態
    self.executedClose_state 為這個 order 平倉倉的狀態
    狀態描述
    self.state_dict = {
            None:'un-execute',
            -1:'margin call',
            -2:'price not available'
        }
    '''

    def __init__(
        self,
        data_center,
        ticker,
        size,
        limit_pending_period, # 限制沒有成交多少天(預設5天)後就取消掛單，可能那時侯還沒有交易日
        additional_info,
        
    ):
        self.data_center = data_center
        self.ticker = ticker
        self.size = size
        
        #
        self.limit_pending_period = limit_pending_period
        #
        self.df_px = data_center.ticker_dict[ticker]
        self.last_tradingDay = self.find_LastTradingDay()
        # 交出開倉訂單
        self.sending_date = None
        # 執行交易後賦值
        self.execued_state = None
        # 執行交易成功賦值
        self.magic_number = None
        self.executed_date = None
        self.executed_price = None
        self.executed_costValue = None
        # 交出平倉訂單
        self.sendingClose_date = None
        # 平倉交易後賦值
        self.executedClose_state = None
        # 平倉交易成功賦值
        self.executedClose_price = None
        self.executedClose_date = None
        self.executedClose_value = None
        self.executedClose_profit = None
        # data center 調整資訊的依據
        self.pendingOpenOrder_orNot = False
        self.pendingCloseOrder_orNot = False
        self.holdedOrder_orNot = False

        #
        self.ExecutedStateDescription_dict = {
            None:'un-execute',
            1:'success',
            2:'has been closed successfully',
            -1:'margin call',
            -2:'price not available',
            -3:'cannot execute because of last trading date'
        }

        self.additional_info = additional_info

    def __check_cash_enough(self,needed_cash):
        return True if self.data_center.cash>=needed_cash else False

    ##### operate orders ##### 

    def execute(self):
        
        # 最後一天交易日日後沒辦法平倉，所以不給開倉，在pendingOpenOrder_orNot上移除
        if self.check_today_is_LastTradingDay_orNot():
            self.execued_state = -3
            self.pendingOpenOrder_orNot = False
            return

        if self.data_center.check_tickerData_available(ticker=self.ticker, type='OPEN'):

            px = self.df_px.loc[self.data_center.date,'OPEN']
            needed_cash = px*self.size

            if self.__check_cash_enough(needed_cash):

                self.execued_state = 1 # success
                
                # 執行訂單的工作
                self.data_center.magic_number += 1
                self.magic_number = self.data_center.magic_number
                self.executed_date = self.data_center.date
                self.executed_price = px
                self.executed_costValue = needed_cash
                # 
                self.data_center.cash = self.data_center.cash - needed_cash
                #
                self.pendingOpenOrder_orNot = False
                self.holdedOrder_orNot = True

            else:
                self.execued_state = -1 # margin call
                self.pendingOpenOrder_orNot = False

        else:
            self.execued_state = -2 # price not available

    def close(self):

        if self.executedClose_state == 1:
            # 已經成功平倉了，不允許再平倉一次
            self.executedClose_state = 2
            self.holdedOrder_orNot = False # 移除掛單
            return

        if self.data_center.check_tickerData_available(ticker=self.ticker, type='OPEN'):
            
            px = self.df_px.loc[self.data_center.date,'OPEN']
            needed_cash = -(px*self.size)

            if self.__check_cash_enough(needed_cash):

                self.executedClose_state = 1 # success

                # 執行訂單的工作
                self.executedClose_price = px
                self.executedClose_date = self.data_center.date
                self.executedClose_value = px*self.size
                self.executedClose_profit = self.executedClose_value - self.executed_costValue
                # 
                self.data_center.cash = self.data_center.cash - needed_cash
                #
                self.pendingCloseOrder_orNot = False
                self.holdedOrder_orNot = False

            else:
                self.executedClose_state = -1 # margin call

        else:
            self.executedClose_state = -2 # price not available

    ##### notify ##### 

    def open_order_notify(self):
        date = self.data_center.date
        StateDescription = self.ExecutedStateDescription_dict[self.execued_state]
        if self.execued_state==None:
            # un-execute
            print(f'{date} {StateDescription}(open) -- {self.ticker} size={self.size}')
        elif self.execued_state==1:
            # success
            print(f'{date} {StateDescription}(open) -- magic number={self.magic_number} ,  {self.ticker} , size={self.size} , value={self.executed_costValue} , executed_price={self.executed_price}')
        elif self.execued_state==-1:
            # margin call
            open_price = self.df_px.loc[date,'OPEN']
            targetValue = open_price*self.size
            print(f'{date} {StateDescription}(open) -- {self.ticker} , remainder_cash={self.data_center.cash} , targetValue={targetValue} , size={self.size}')
        elif self.execued_state==-2:
            # price not available
            print(f'{date} {StateDescription}(open) -- {self.ticker} size={self.size}')
        elif self.execued_state==-3:
            # cannot execute because of last trading date
            print(f'{date} {StateDescription}(open) -- {self.ticker} size={self.size}')
        else:
            # unknow state
            print(f'{date} unknow state(close) -- {self.ticker} , size={self.size} , sending_date={self.sending_date}')

    def close_order_notify(self):
        date = self.data_center.date
        StateDescription = self.ExecutedStateDescription_dict[self.executedClose_state]
        if self.executedClose_state==None:
            # un-execute
            print(f'{date} {StateDescription}(close) -- magic number={self.magic_number} , {self.ticker} size={self.size}')
        elif self.executedClose_state==1:
            # success
            print(f'{date} {StateDescription}(close) -- magic number={self.magic_number} , {self.ticker} , size={self.size}, value={self.executedClose_value} , close_price={self.executedClose_price}')
        elif self.executedClose_state==2:
            # has been closed successfully
            print(f'{date} {StateDescription}(close) -- magic number={self.magic_number} , {self.ticker} size={self.size}')
        elif self.executedClose_state==-1:
            # margin call
            open_price = self.df_px.loc[date,'OPEN']
            targetValue = -(open_price*self.size)
            print(f'{date} {StateDescription}(close) -- {self.ticker} , remainder_cash={self.data_center.cash} , targetValue={targetValue} , size={self.size}')
        elif self.executedClose_state==-2:
            # price not available
            print(f'{date} {StateDescription}(close) -- {self.ticker} size={self.size}')
        else:
            # unknow state
            print(f'{date} unknow state(close) -- {self.ticker} , size={self.size} , sendingClose_date={self.sendingClose_date}')


    ##### calculate ##### 

    def calculate_CurrentValue(self):
        date = self.data_center.find_TheMostRecentDate_InWhichDataIsAvailable(ticker=self.ticker, type='CLOSE')
        if date:
            px = self.df_px.loc[date,'CLOSE']
            CurrentValue = px*self.size
            return CurrentValue
        else:
            return np.nan

    def calculate_NetValue(self):
        CurrentValue = self.calculate_CurrentValue()
        NetValue = np.nan if np.isnan(CurrentValue) else CurrentValue-self.executed_value
        return NetValue

    def calculate_pendingOpen_peirod(self):
        '''計算開倉掛單未成交多少天'''
        today = self.data_center.date
        return (today-self.sending_date)/datetime.timedelta(days=1)
    
    def calculate_pendingClose_peirod(self):
        '''計算平倉掛單未成交多少天'''
        today = self.data_center.date
        return (today-self.sendingClose_date)/datetime.timedelta(days=1)

    def calculate_return_rate(self):
        if self.executedClose_state and self.execued_state:
            return self.executedClose_price/self.executed_price -1 

        else:
            return np.nan

    def calculate_annual_return_rate(self):
        return_rate = self.calculate_return_rate()
        if not np.isnan(return_rate):
            holding_year_period = self.calculate_holding_period()/252
            return return_rate/holding_year_period
        else:
            return np.nan

    def calculate_entire_holding_period(self):
        # 必須成功開倉平倉，要不然回傳NA
        if self.executedClose_state and self.execued_state:
            start_idx = self.data_center.dateList.index(self.executed_date)
            end_idx = self.data_center.dateList.index(self.executedClose_date)

            return end_idx-start_idx

        else:
            return np.nan

    def calculate_holding_period(self):
        if self.execued_state:
            start_idx = self.data_center.dateList.index(self.executed_date)
            end_idx = self.data_center.dateList.index(self.data_center.date)
            return end_idx-start_idx
        else:
            return np.nan


    ##### find #####
    def find_LastTradingDay(self):
        '''
        找這個標的最後一個交易日。
        利用 data_center 中限定的交易區間中(self.data_center.dateList)找到這個標的最後一個交易日
        '''
        df_sub_px = self.df_px.loc[self.data_center.dateList,'OPEN']
        return df_sub_px.index[-1]


    ##### check #####

    def check_today_is_LastTradingDay_orNot(self):
        '''
        LastTradingDay的定義，取決於是否要再回測最後一天(self.data_center.dateList[-1])平倉。
        if self.data_center.close_at_BacktestingEndDate_orNot==True:
            LastTradingDay = 股票資料的最後一天or回測日最後一天
        if self.data_center.close_at_BacktestingEndDate_orNot==False:
            LastTradingDay = 股票資料的最後一天，且非回測日最後一天(因為之後還會有資料)
        
        '''
        df_px = self.df_px.dropna() # dropna 是為了確保今天是這個標的倒數兩天有價格的日期
        today = self.data_center.date
        # 該標的本身價格最後時間點
        condition1 = today==df_px.index[-1]
        # 策略最後時間點
        condition2 = today==self.data_center.dateList[-1]
        if self.data_center.close_at_BacktestingEndDate_orNot:
            return condition1|condition2
        else:  
            return condition1 and (not condition2)

    def check_tomorrow_is_LastTradingDay_orNot(self):
        df_px = self.df_px.dropna() # dropna 是為了確保今天是這個標的倒數兩天有價格的日期
        today = self.data_center.date
        # 該標的本身價格最後送出掛單的時間點
        condition1 = today==df_px.index[-2]
        # 策略最後送出掛單的時間點
        condition2 = today==self.data_center.dateList[-2]
        if self.data_center.close_at_BacktestingEndDate_orNot:
            return condition1|condition2
        else:  
            return condition1 and (not condition2)

   



