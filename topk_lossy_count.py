import pickle as pkl
import os
import pandas as pd

def load_topk(path = None):
    if path == None:
        # get parent directory path
        parent_dir = os.path.dirname(__file__)
        path = os.path.join(parent_dir, 'POI_data', 'topk.pkl')
    else:
        path = os.path.join(path,'topk.pkl')
    try:
        with open(path, 'rb') as f:
            topk_counter= pkl.load(f)
    except FileNotFoundError:
        topk_counter = {}
    return topk_counter

def save_topk(topk,path = None):
    if path == None:
        # get parent directory path
        parent_dir = os.path.dirname(__file__)
        path = os.path.join(parent_dir, 'POI_data', 'topk.pkl')
    else:
        path = os.path.join(path,'topk.pkl')
    with open(path, 'wb') as f:
        pkl.dump(topk, f)

# topk counter structure:
'''
{personid :{ category : { 'bucket_num': value, 'total_num':value, 'freq': pandasDataFram}}}
pandas DataFrame includes columns: venueid, freq, buecket_i
'''

def update_topk(topk_counter, daily_activities, bucket_size=5):
   """使用新格式的Lossy Counting更新"""
   for persona_id, dates in daily_activities.items():
       if persona_id not in topk_counter:
           topk_counter[persona_id] = {}
           
       for date, activities in dates.items():
           for activity in activities:
               activity_type = activity[1]
               location_id = activity[3]

               # 初始化新的类别
               if activity_type not in topk_counter[persona_id]:
                   topk_counter[persona_id][activity_type] = {
                       'bucket_num': 0,
                       'total_num': 0,
                       'freq': pd.DataFrame(columns=['venue_id', 'freq', 'bucket_i'])
                   }
               
               cat_data = topk_counter[persona_id][activity_type]
               freq_df = cat_data['freq']
               # 更新频率
               if location_id in freq_df['venue_id'].values:
                   # 更新已存在的venue
                   idx = freq_df.index[freq_df['venue_id'] == location_id][0]
                   freq_df.at[idx, 'freq'] += 1
               else:
                   # 添加新的venue
                   new_row = pd.DataFrame({
                       'venue_id': [location_id],
                       'freq': [1],
                       'bucket_i': [cat_data['bucket_num'] - 1]
                   })
                   freq_df = pd.concat([freq_df, new_row], ignore_index=True)
               
               # 更新总数
               cat_data['total_num'] += 1
               
               # 检查是否需要清理
               if cat_data['total_num'] %bucket_size ==0:
                   # 清理
                   mask = freq_df['freq'] + freq_df['bucket_i'] > cat_data['bucket_num']
                   freq_df = freq_df[mask]
                   
                   # 重置计数器
                   cat_data['bucket_num'] += 1
               
               # 更新DataFrame
               cat_data['freq'] = freq_df
               
   return topk_counter

# topk counter structure:
'''
{personid :{ category : { -1 :  [bucket_num, num], venueid : [ freq , bucket_i]}}}
'''
'''
def update_topk_old(topk_counter, daily_activities, bucket_size=5, persona_data=None) :
    """
    Update top-k frequent locations using Lossy Counting algorithm
    
    Args:
        topk_counter (dict): Current counter state
        daily_activities (dict): Activities data structured as {persona_id: {date: [activities]}}
        bucket_size (int): Size of the bucket (⌈1/ε⌉)
        persona_data (dict, optional): Additional persona information for filtering
    
    Returns:
        dict: Updated topk_counter
    """
    for persona_id, dates in daily_activities.items():
        for date, activities in dates.items():
            for activity in activities:
                # Filter conditions
                is_basic_location = activity[1] in ['Home', 'Workplace']
                is_student_education = (persona_data and 
                                     persona_id in persona_data and 
                                     activity[0] == 'education' and 
                                     persona_data[persona_id].get("occupation") == 'student')
                
                if not is_basic_location and not is_student_education:
                    # Initialize counter structures if needed
                    if persona_id not in topk_counter:
                        topk_counter[persona_id] = {}
                    
                    activity_type = activity[1]
                    location_id = activity[4]
                    
                    if activity_type not in topk_counter[persona_id]:
                        # Initialize new location type with bucket counter
                        # [-1] key stores [current_bucket_number, elements_in_current_bucket]
                        topk_counter[persona_id][activity_type] = {-1: [1, 0]}
                    
                    if location_id not in topk_counter[persona_id][activity_type]:
                        # Add new location with [count, delta]
                        current_bucket = topk_counter[persona_id][activity_type][-1][0]
                        topk_counter[persona_id][activity_type][location_id] = [1, current_bucket - 1]
                    else:
                        # Increment existing location counter
                        topk_counter[persona_id][activity_type][location_id][0] += 1
                    
                    # Update bucket counter
                    topk_counter[persona_id][activity_type][-1][1] += 1
                    
                    # Check if current bucket is full
                    if topk_counter[persona_id][activity_type][-1][1] == bucket_size:
                        # Reset bucket counter and start cleaning
                        topk_counter[persona_id][activity_type][-1][1] = 0
                        current_bucket = topk_counter[persona_id][activity_type][-1][0]
                        
                        # Identify items to remove
                        items_to_remove = [
                            key for key, value in topk_counter[persona_id][activity_type].items()
                            if key != -1 and value[0] + value[1] <= current_bucket
                        ]
                        
                        # Remove items
                        for key in items_to_remove:
                            del topk_counter[persona_id][activity_type][key]
                        
                        # Increment bucket number
                        topk_counter[persona_id][activity_type][-1][0] += 1
    
    return topk_counter
'''