'''
Tools to mimic R's dplyr
'''
import pandas as pd
import sys

class NotDataFrameException(Exception):
    def __init__(self, value):
        message = 'One of the inputs is not a pandas DataFrame.'
        super().__init__(message)
        
        
def trigger_not_df(obj):
    if not isinstance(obj, pd.DataFrame):
        raise NotDataFrameException(obj)
       
        
# dplyr::anti_join()    
def anti_join(x, y, on):
    trigger_not_df(x)
    trigger_not_df(y)
    #Return rows in x which are not present in y
    ans = pd.merge(left=x, right=y, how='left', indicator=True, on=on)
    ans = ans.loc[ans._merge == 'left_only', :].drop(columns='_merge')
    return ans
      
    
# Works like dplyr::select(cols + everything()) or Stata's order
def order_columns(df, list_of_first_cols):
    trigger_not_df(df)
    if not isinstance(list_of_first_cols, list):
        sys.exit('2nd argument must be a list of column names')
    cols = list_of_first_cols
    df = df[cols + [c for c in df.columns if c not in cols]]
    return df

# for testing
if __name__=='__main__':
    df1 = pd.DataFrame({'car':['Audi','Toyota'],'mpg':[25,30]})
    df2 = pd.DataFrame({'car':['Toyota'],'mpg':[30]})
    list1 = [1,2,3,4]
    list2 = list(range(1,1001))

