import pandas as pd
import numpy as np
import datetime

class Analysis:

    def __init__(self,data_center):
        self.data_center = data_center
        self.ticker_dict = data_center.ticker_dict
        self.dateList = data_center.dateList
        self.start_date = data_center.start_date
        self.order_records = data_center.order_records

        self.value_list = data_center.value_list
        self.cash_list = data_center.cash_list

        self.orders_InfoTable = None

        #
        self.account_timeseries_state = pd.DataFrame()



    def get_orders_InfoTable(self):
        
        order_info_dict = dict()
        #
        order_info_dict['magic_number'] = [order_obj.magic_number for order_obj in self.order_records]
        order_info_dict['ticker'] = [order_obj.ticker for order_obj in self.order_records]
        order_info_dict['size'] = [order_obj.size for order_obj in self.order_records]
        # date
        order_info_dict['sending_date'] = [order_obj.sending_date for order_obj in self.order_records]
        order_info_dict['executed_date'] = [order_obj.executed_date for order_obj in self.order_records]
        order_info_dict['sendingClose_date'] = [order_obj.sendingClose_date for order_obj in self.order_records]
        order_info_dict['executedClose_date'] = [order_obj.executedClose_date for order_obj in self.order_records]
        order_info_dict['holding_period'] = [order_obj.calculate_entire_holding_period() for order_obj in self.order_records]
        # price&value
        order_info_dict['executed_price'] = [order_obj.executed_price for order_obj in self.order_records]
        order_info_dict['executedClose_price'] = [order_obj.executedClose_price for order_obj in self.order_records]
        order_info_dict['executed_costValue'] = [order_obj.executed_costValue for order_obj in self.order_records]
        order_info_dict['executedClose_profit'] = [order_obj.executedClose_profit for order_obj in self.order_records]
        #
        order_info_dict['return_rate'] = [order_obj.calculate_return_rate() for order_obj in self.order_records]
        order_info_dict['annual_return_rate'] = [order_obj.calculate_annual_return_rate() for order_obj in self.order_records]
        # state
        order_info_dict['execued_state'] = [order_obj.execued_state for order_obj in self.order_records]
        order_info_dict['executedClose_state'] = [order_obj.executedClose_state for order_obj in self.order_records]

        orders_InfoTable = pd.DataFrame(order_info_dict)
        orders_InfoTable = orders_InfoTable[~orders_InfoTable['magic_number'].isna()]
        orders_InfoTable = orders_InfoTable.set_index('magic_number').sort_index()
        
        self.orders_InfoTable = orders_InfoTable
        return orders_InfoTable


    def win_rate(self):

        dummy_series = self.orders_InfoTable.apply(
            lambda row:1 if row['return_rate']>0 else 0,
            axis=1
        )
        return dummy_series.sum()/len(dummy_series)

    def calculate_annualized_return(self):
        return_mean = self.strategy_daily_return().mean()
        annualized_return = return_mean*252
        return annualized_return

    def calculate_annualized_volatility(self):
        return_std = self.strategy_daily_return().std()
        annualized_std = return_std*(252**0.5)
        return annualized_std

    def calculate_annualized_sharpe_ratio(self):
        return self.calculate_annualized_return()/self.calculate_annualized_volatility()


    def get_account_timeseries_state(self):
        self.account_timeseries_state = self.data_center.get_account_timeseries_state()
        return self.account_timeseries_state

    def strategy_daily_return(self):

        if len(self.account_timeseries_state)==0:
            self.account_timeseries_state = self.data_center.get_account_timeseries_state()

        return_series = self.account_timeseries_state['value'].pct_change().rename('return')
        return_series = return_series.replace(np.nan, 0.0) # 計算報酬率，起始時還不能算預設填入na，我這裡改成0

        return return_series

    def calculate_rolling_annualized_volatility(self,period):
        return_series = self.strategy_daily_return()
        return return_series.rolling(window=period).std()*(252**0.5)

    def calculate_rolling_annualized_return(self,period):
        return_series = self.strategy_daily_return()
        return return_series.rolling(window=period).mean()*252

    def calculate_rolling_annualized_sharpe_ratio(self,period):
        return self.calculate_rolling_annualized_return(period)/self.calculate_rolling_annualized_volatility(period)

    def get_transactions(self):
        '''
        得到所有時間點進行的交易，這裡不討論是平倉還是開倉，只管買進或賣出多少單位
        '''
        orders_InfoTable = self.get_orders_InfoTable().reset_index()

        tran_dict = dict()
        tran_dict['date'] = orders_InfoTable['executed_date']
        tran_dict['amount'] = orders_InfoTable['size']
        tran_dict['price'] = orders_InfoTable['executed_price']
        tran_dict['sid'] = orders_InfoTable.index
        tran_dict['symbol'] = orders_InfoTable['ticker']
        tran_dict['value'] = orders_InfoTable['executed_costValue']

        transactions = pd.DataFrame(
            {
                'date':orders_InfoTable['executed_date'],
                'amount':orders_InfoTable['size'],
                'price':orders_InfoTable['executed_price'],
                'sid':orders_InfoTable['magic_number'],
                'symbol':orders_InfoTable['ticker'],
                'value':orders_InfoTable['executed_costValue']
            }
        ).set_index('date').sort_index()
        

        return transactions


    def setup_for_pyfolio(self):

        returns = self.strategy_daily_return()
        transactions = self.get_transactions()

        # pyfolio 要經過轉換成 datetime.date 才能 work
        dateList = [self.__datetimedatetime_to_datetimedate(day) for day in self.data_center.dateList]
        cash = pd.DataFrame({'cash':self.data_center.cash_list}, index=dateList)
        positions = self.data_center.HoldingTicker_size
        positions = pd.concat([positions, cash], axis=1)

        returns = returns[returns.index>=self.data_center.strategy_execute_start_date]
        positions = positions[positions.index>=self.data_center.strategy_execute_start_date]
        transactions = transactions[transactions.index>=self.data_center.strategy_execute_start_date]


        return returns, positions, transactions

    def calculate_the_contribution_of_individual_tickers(self):
        '''
        計算每個ticker對於整個策略有多少貢獻。
        貢獻定義:
            找到某個ticker所有的order，
            計算該筆order的貢獻(賺的金額/開倉時帳戶總市值)，
            再把每一筆交易貢獻加總，就是該ticker的貢獻。
        '''
        individual_ticker_return_sum_dict = dict()
        for ticker in set(self.orders_InfoTable['ticker']):
            temp_df = self.orders_InfoTable[self.orders_InfoTable['ticker']==ticker]
            return_sum = 0
            for i in range(len(temp_df)):
                info_dict = dict(temp_df.iloc[i,:])
                return_rate = self.__calcualte_return_of_order_for_account_value(info_dict)
                return_sum = return_sum + return_rate
            individual_ticker_return_sum_dict[ticker] = return_sum
        individual_ticker_return_series = pd.Series(individual_ticker_return_sum_dict).sort_values()
        return individual_ticker_return_series

        
    def plot_the_contribution_of_individual_tickers(self,figsize=(30,5)):
        individual_ticker_return_series = self.calculate_the_contribution_of_individual_tickers()
        individual_ticker_return_series.plot.bar(figsize=figsize)


    # private method
    def __datetimedatetime_to_datetimedate(self,date):
        '''date 為 datetime.datetime，轉換成datetime.date'''
        return datetime.date(date.year, date.month, date.day)

    def __calcualte_return_of_order_for_account_value(self,info_dict):
        '''
        input:
            info_dict : 為 orders_InfoTable 的一個row轉成字典 (一個order的資訊)
        '''
        executedClose_profit = info_dict['executedClose_profit']
        executed_date = info_dict['executed_date']
        account_value_when_open = self.account_timeseries_state.loc[executed_date,'value']
        return executedClose_profit/account_value_when_open
