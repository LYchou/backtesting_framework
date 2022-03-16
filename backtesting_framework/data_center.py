
import pandas as pd
import numpy as np

class Data_center:

    def __init__(self,ticker_dict,dateList,start_date,end_date,strategy_execute_start_date,value,cash,notify_orNot,close_at_BacktestingEndDate_orNot):
        self.ticker_dict = ticker_dict
        self.indicator = {}
        self.dateList = dateList
        self.start_date = start_date
        self.end_date = end_date
        # 開始執行策略(next)的第一天
        self.strategy_execute_start_date = strategy_execute_start_date if strategy_execute_start_date else start_date
        self.date = dateList[0] # 迭代第一天
        self.value = value
        self.cash = cash
        self.notify_orNot = notify_orNot
        self.close_at_BacktestingEndDate_orNot = close_at_BacktestingEndDate_orNot # 控制是否要再回測日最後一天平倉
        self.magic_number = 0
        self.pending_open_orders = []
        self.pending_close_orders = []
        self.holded_orders = []
        self.order_records = []
        self.value_list = []
        self.cash_list =[]

        self.HoldingTicker_MarketValue = pd.DataFrame(
            {ticker:[0]*len(dateList) for ticker in ticker_dict.keys()},
            index=self.dateList
        )
        self.HoldingTicker_size = pd.DataFrame(
            {ticker:[0]*len(dateList) for ticker in ticker_dict.keys()},
            index=self.dateList
        )
        



    ##### get #####

    def get_order_by_magic_number(self,magic_number):
        orders_list = [order_obj for order_obj in self.holded_orders if order_obj.magic_number==magic_number]
        if orders_list:
            return orders_list[0]
        else:
            return None

    def get_orders_by_ticker(self,ticker):
        return [order_obj for order_obj in self.holded_orders if order_obj.ticker==ticker]

    def get_HoldedTotalSize_of_ticker(self,ticker):
        sizes = [order_obj.size for order_obj in self.holded_orders if order_obj.ticker==ticker]
        return sum(sizes)
    
    def get_HoldedTotalValue_of_ticker(self,ticker):

        orders = self.get_orders_by_ticker(ticker) # 只到ticker所有的orders，若沒有則回傳 []
        value = 0
        for order_obj in orders:
            value = value + order_obj.calculate_CurrentValue()
        return value

    def get_HoldedTotalCost_of_ticker(self,ticker):
        orders = self.get_orders_by_ticker(ticker)
        total_cost = 0
        for order_obj in orders:
            total_cost = total_cost + order_obj.executed_costValue

        return total_cost

    def get_holded_tickers(self):
        return list(set(order_obj.ticker for order_obj in self.holded_orders))
    

    def get_account_timeseries_state(self):
        if self.date==self.end_date:
            return pd.DataFrame(
                {
                    'value':self.value_list,
                    'cash':self.cash_list
                },
                index = self.dateList
            )

    def get_ticker_pxdf_rolling_subindex(self,ticker,formation_period):
        '''
        功能:
            用於 rolling 整張 df, 這樣 rolling 可以同時檢所所有col
        回傳 [[subindex],[subindex],...,[subindex]]
        subindex = df.index[i]往前數formation_period的index if i>=formation_period else np.nan
        '''
        idx = self.ticker_dict[ticker].index
        return [idx[i-formation_period:i] if i>=formation_period else [np.nan] for i in range(len(idx))]

    def get_past_Ndays_dateList(self, N):
        '''
        回傳過去N天的 sub dateList (包含今天)
        '''
        today = self.date
        today_idx = self.dateList.index(today)
        # 說明下面的 index
        # N : 代表取得的天數
        # 由於回傳的 sub dateList 要包含 today 所以，後面的index要加1(today_idx+1)
        # 由於要回傳天數為N的list，前面的index要設成today_idx-N+1，才滿足 (today_idx+1)-(today_idx-N+1) = N
        start_idx = today_idx-N+1 if (today_idx-N+1)>0 else 0
        end_idx = today_idx+1
        return self.dateList[start_idx:end_idx]

    def get_past_Ndays_dateList_before_Mdays(self, N, M):
        '''
        回傳過去N天的 sub dateList (包含今天)
        '''
        today = self.date
        today_idx = self.dateList.index(today)
        # 說明下面的 index
        # N : 代表取得的天數
        # 由於回傳的 sub dateList 要包含 today 所以，後面的index要加1(today_idx+1)
        # 由於要回傳天數為N的list，前面的index要設成today_idx-N+1，才滿足 (today_idx+1)-(today_idx-N+1) = N
        start_idx = today_idx-N+1-M if (today_idx-N+1-M)>0 else 0
        end_idx = today_idx+1-M
        return self.dateList[start_idx:end_idx]

    def get_next_trading_date(self):
        today_idx = self.dateList.index(self.date)
        next_trading_date_idx = today_idx+1
        return self.dateList[next_trading_date_idx]
    
    def get_previous_trading_date(self):
        today_idx = self.dateList.index(self.date)
        previous_trading_date_idx = today_idx-1
        return self.dateList[previous_trading_date_idx]
        

    ##### calculate #####

    def calculate_HoldedTotal_return_rate(self,ticker):
        total_cost = self.get_HoldedTotalCost_of_ticker(ticker)
        total_value = self.get_HoldedTotalValue_of_ticker(ticker)
        return total_value/total_cost -1
    
    def calculate_residual_series(self,X,y):
        '''
        fit的完回歸，直接計算殘插回傳
        '''
        from sklearn.linear_model import LinearRegression

        reg = LinearRegression().fit(X, y)
        residual_series = y-reg.predict(X)
        residual_series = residual_series.iloc[:,0] # series
        return residual_series

    def fit_regression(self,X,y):
        '''
        fit完，把物件傳出去
        '''
        from sklearn.linear_model import LinearRegression
        reg_obj = LinearRegression().fit(X, y)
        return reg_obj

    def get_residual_series(self,reg_obj,X,y):
        '''
        利用fit的完的物件，對資料計算殘差
        '''
        residual_series = y-reg_obj.predict(X)
        residual_series = residual_series.iloc[:,0] # series
        return residual_series

    ##### check #####

    def check_tickerData_available(self, ticker, type, date=None):
        '''
        type : 輸入 ticker_dict[ticker]的欄位名稱
        '''
        date = date if date else self.date # 如果date為None傳入今天日期，否則維持原輸入
        if date not in self.ticker_dict[ticker].index:
            # 根本沒有今天資料
            return False
        else:
            # 看看價格是否為空值
            data = self.ticker_dict[ticker].loc[date, type]
            return not np.isnan(data)

    ##### find #####

    def find_TheMostRecentDate_InWhichDataIsAvailable(self, ticker, type, pastLimit=10):
        '''
        功能:
            找到過去有值的日期。找不到則回傳 NA
        使用場景:
            今天該股票沒有價格，而我手上有持有這檔股票，我要計算market value 可以用
        參數:
            pastLimit : 最多往過去找幾天的價格，如果指太多天還是NA似乎也不合理，就預設找10天就好了
        '''
        today_idx = self.dateList.index(self.date)
        idx  = today_idx
        backCount = 0
        while True:
            date = self.dateList[idx-backCount]
            if self.check_tickerData_available(ticker=ticker, type=type, date=date):
                return date
            else:
                backCount +=1
                if backCount==pastLimit:
                    return None

    def find_TheStartDate_of_ThisMonth(self,year,month):
        '''
        目的:
            找到 target_date 這天這個月，在資料中這個月的第一天
        output:
            target_date : datetime.datetime格式
        '''
        this_month_dateList = list(
            filter(
                lambda date: date.year==year and date.month==month,
                self.dateList
            )
        )
        start_of_month = min(
            this_month_dateList,
            key=lambda date:date.day
        )
        return start_of_month

    def find_TheStartDates_of_TheseMonths(self):
        year_month_set = {
            (date.year,date.month) for date in self.dateList
        }

        TheStartDates_of_TheseMonths = [
            self.find_TheStartDate_of_ThisMonth(year,month) for year,month in year_month_set
        ]
        TheStartDates_of_TheseMonths.sort()
        return TheStartDates_of_TheseMonths


    def find_TheEndDate_of_ThisMonth(self,year,month):
        '''
        目的:
            找到 target_date 這天這個月，在資料中這個月的最後一天
        output:
            target_date : datetime.datetime格式
        '''
        this_month_dateList = list(
            filter(
                lambda date: date.year==year and date.month==month,
                self.dateList
            )
        )
        end_of_month = max(
            this_month_dateList,
            key=lambda date:date.day
        )
        return end_of_month

    def find_TheEndDates_of_TheseMonths(self):
        year_month_set = {
            (date.year,date.month) for date in self.dateList
        }

        TheEndDates_of_TheseMonths = [
            self.find_TheEndDate_of_ThisMonth(year,month) for year,month in year_month_set
        ]
        TheEndDates_of_TheseMonths.sort()
        return TheEndDates_of_TheseMonths
    

    def find_TheTargetDate_of_ThisMonth(self,year,month,target_day):
        '''
        目的:
            找到 target_date 這天這個月，在資料中這個月離target_day號最近的交易日
        output:
            target_date : datetime.datetime格式
        '''
        this_month_dateList = list(
            filter(
                lambda date: date.year==year and date.month==month,
                self.dateList
            ))
        target_day_of_month = min(
            this_month_dateList,
            key=lambda date:abs(date.day-target_day)
        )
        return target_day_of_month

    def find_TheTargetDates_of_TheseMonths(self,target_day):
        year_month_set = {
            (date.year,date.month) for date in self.dateList
        }

        TheTargetDates_of_TheseMonths = [
            self.find_TheTargetDate_of_ThisMonth(year,month,target_day) for year,month in year_month_set
        ]
        TheTargetDates_of_TheseMonths.sort()
        return TheTargetDates_of_TheseMonths

        
    def find_TheMidDates_of_TheseMonths(self):
        return self.find_TheTargetDates_of_TheseMonths(target_day=15)



