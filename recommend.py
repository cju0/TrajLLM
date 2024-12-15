import pickle as pkl
import json
import os
from densmapClass import * 
import numpy as np
import pandas as pd


# # get current absolute path
# abs_file_path = os.path.abspath(__file__)
# # get current work directory path
# current_dir = os.path.dirname(__file__)
# # get parent directory path
# parent_dir = os.path.dirname(os.path.dirname(__file__))
# path = parent_dir+'\\POI_data\\'
# with open(path+ 'cat_map', 'r') as f:
#     tag_dict = json.load(f)

# tag_dict = eval(str(tag_dict))

def read_densmaps(path = None):
    # get parent directory path
    if path == None:
        # get parent directory path
        # parent_dir = os.path.dirname(os.path.dirname(__file__))
        parent_dir = os.path.dirname(__file__)
        path = os.path.join(parent_dir, 'POI_data', 'densMaps.pkl')
    else:
        path = os.path.join(parent_dir,'densMaps.pkl')
    try:
        with open(path, 'rb') as f:
            densmaps= pkl.load(f)
    except FileNotFoundError:
        print("Density Matrix File doesn't exsit, run gen_densMatrix First")
        return FileNotFoundError("Density Matrix File is missing") 
    return densmaps

def calculate_weight(row,densmap,user_loc):
    x = row['xIndex']
    y = row['yIndex']
    dist = geodesic(user_loc, (row['lat'], row['lng'])).m
    return densmap[x, y] / ((dist+50) ** 1.5)


# with open(paht+ 'densMaps.pkl', 'rb') as file:
#     densmap = pickle.load(file)

# print(densmap.locO)

'''
 old recommend function
def recommend(user_loc, activity, densmap, model='gravity'):
    tag = activity[1]
    

    if model == 'gravity':
        dens_matirx = densmap[tag]
        poi_set = pd.read_csv(tag+'_ca_poi.csv')
        candidate = compute_weight_gravity(user_loc, dens_matirx, poi_set)
        random_row = candidate.sample(n=1, weights='weight')
        result = random_row['ID'], [random_row['lat'],random_row['lng']]
        return result
    elif model == 'mix':
        pass
'''



def recommend(user_loc, activity, densmap, user_id, topk_counter, model='gravity', path=None, alpha=0.05):
   '''
   model = 'gravity' or 'mix
   '''
   
   tag = activity[1]

   if path == None:
        parent_dir = os.path.dirname(__file__)
        # parent_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(parent_dir, 'POI_data', tag+'_ca_poi.csv')
   else:
        path = os.path.join(path,tag+'_ca_poi.csv')
   
   # 读取POI数据集
   poi_set = pd.read_csv(path)

   if model == 'gravity':
        dens_matrix = densmap[tag]
        candidate = compute_weight_gravity(user_loc, dens_matrix, poi_set)
       
        if len(candidate) > 0:
            random_row = candidate.sample(n=1, weights='weight')
            result = random_row['ID'].iloc[0], [random_row['lat'].iloc[0], random_row['lng'].iloc[0]]
        else:
            print('cannot find candiate in this poi set')
            result = None, None
            
        return result
    
   elif model == 'mix':
        # 获取gravity模型的推荐
        dens_matrix = densmap[tag]
        gravity_candidate = compute_weight_gravity(user_loc, dens_matrix, poi_set)
        gravity_candidate = gravity_candidate.rename(columns={'ID': 'venue_id', 'weight': 'gravity_weight'})

        # 获取topk推荐
        topk_candidate = recommend_from_topk(user_id, tag, topk_counter)

        if len(gravity_candidate) == 0 and len(topk_candidate) == 0:
            print('Something Error: not candidate from gravity model and topk')
            result = None, None
            return None, None
        # print(gravity_candidate)
        # 合并两个推荐结果
        merged_df = pd.merge(
            gravity_candidate[['venue_id', 'gravity_weight','lat','lng']], 
            topk_candidate[['venue_id', 'weight']], 
            on='venue_id', 
            how='outer'
        ).fillna(0)  # 填充缺失值为0
        
        # 计算混合权重
        merged_df['final_weight'] = (1-alpha) * merged_df['gravity_weight'] + alpha * merged_df['weight']
        # print(merged_df)
        # print(merged_df[merged_df['venue_id']==topk_candidate['venue_id'][0]])

       # 标准化权重
        if merged_df['final_weight'].sum() > 0:
            merged_df['final_weight'] = merged_df['final_weight'] / merged_df['final_weight'].sum()

        # 随机选择一个venue
        if len(merged_df) > 0:
            selected_venue = merged_df.sample(n=1, weights='final_weight')
            venue_id = selected_venue['venue_id'].iloc[0]
            
            # 获取位置信息
            venue_info = poi_set[poi_set['ID'] == venue_id]
            if len(venue_info) > 0:
                result = venue_id, [venue_info['lat'].iloc[0], venue_info['lng'].iloc[0]]
            else:
                result = None, None
        else:
            print('Something Error: not candidate from gravity model and topk')
            result = None, None
            
        return result
       
   else:
       return None, None



def compute_weight_gravity(user_loc, dens_matrix, poi_set, r=10000):
    # 获取密度矩阵的大小
    xSize, ySize = dens_matrix.densmap.shape
    
    # get user index
    user_idx = (np.array(latlng2meter(dens_matrix.locO,user_loc))//dens_matrix.partitionSize).astype(int)
    R = int(-((-r)//dens_matrix.partitionSize))
    center = R//2
    R = center*2 + 1
    
    # if user loc out of range
    def handle_out_of_bounds(user_idx, xSize, ySize):
        x, y = user_idx
        
        # 情况1：完全超出范围 - 使用最近的边界点
        x = np.clip(x, 0, xSize-1)
        y = np.clip(y, 0, ySize-1)
        
        return np.array([x, y])
    
    # if out of range
    original_user_idx = user_idx.copy()
    user_idx = handle_out_of_bounds(user_idx, xSize, ySize)
    
    # 生成势能矩阵
    potential = np.zeros((R,R))
    for i in range(R):
        for j in range(R):
            if i == center and j == center:
                potential[i,j] = 1
            else:
                potential[i,j] = 1/(np.sqrt(abs(i-center)**2+abs(j-center)**2))**1.5
    
    # 处理flow矩阵的边界情况
    def get_valid_slice(idx, center, size):
        start = max(0, idx-center)
        end = min(size, idx+center+1)
        matrix_start = max(0, center-(idx-start))
        matrix_end = min(R, center+(end-idx))
        return slice(start, end), slice(matrix_start, matrix_end)
    
    # 获取有效的切片范围
    x_slice_dens, x_slice_pot = get_valid_slice(user_idx[0], center, xSize)
    y_slice_dens, y_slice_pot = get_valid_slice(user_idx[1], center, ySize)
    
    # 创建填充了0的完整大小流矩阵
    flow = np.zeros((R, R))
    flow[x_slice_pot, y_slice_pot] = dens_matrix.densmap[x_slice_dens, y_slice_dens]
    
    # 应用势能
    flow = flow * potential
    
    # 获取top k网格
    k = 25
    flattened_flow = flow.flatten()
    top_k_indices_flat = np.argpartition(flattened_flow, -k)[-k:]
    top_k_values = flattened_flow[top_k_indices_flat]
    
    top_k_indices_2d = np.unravel_index(top_k_indices_flat, flow.shape)
    
    # 转换索引到原始矩阵
    top_k_indices_2d = list(top_k_indices_2d)
    top_k_indices_2d[0] = np.clip(top_k_indices_2d[0]-center+user_idx[0], 0, xSize-1)
    top_k_indices_2d[1] = np.clip(top_k_indices_2d[1]-center+user_idx[1], 0, ySize-1)
    
    # 筛选候选点
    candidate = poi_set[
        (poi_set['xIndex'].isin(top_k_indices_2d[0])) & 
        (poi_set['yIndex'].isin(top_k_indices_2d[1]))
    ].copy()
    
    # 如果候选集为空，选择最近的几个点
    if len(candidate) == 0:
        # 计算所有POI到用户的距离
        poi_coords = poi_set[['lat', 'lng']].values
        user_coord = np.array(user_loc)
        distances = np.sqrt(np.sum((poi_coords - user_coord)**2, axis=1))
        closest_indices = np.argsort(distances)[:k]
        candidate = poi_set.iloc[closest_indices].copy()
    
    # 重置索引并计算权重
    candidate = candidate.reset_index(drop=True)
    candidate['weight'] = candidate.apply(
        lambda x: calculate_weight(x, dens_matrix.densmap, user_loc), 
        axis=1
    )
        # 选取权重最高的top 100
    if len(candidate) > 100:
        candidate = candidate.nlargest(100, 'weight')
    
    
    # 标准化权重
    if candidate['weight'].sum() > 0:
        candidate['weight'] = candidate['weight']/candidate['weight'].sum()
    else:
        # 如果所有权重都是0，使用均匀分布
        candidate['weight'] = 1.0/len(candidate)
    
    # 添加距离信息供参考
    candidate['distance_to_user'] = candidate.apply(
        lambda x: geodesic(user_loc, (x['lat'], x['lng'])).m, 
        axis=1
    )
    
    return candidate



def recommend_from_topk(userid, category, topk_counter):
    """
    根据lossy counting的结果生成推荐
    
    Parameters:
    -----------
    userid: 用户ID
    category: 类别
    topk_counter: 新格式的计数器
    
    Returns:
    --------
    pd.DataFrame: 包含venue_id和weight列的DataFrame
    """
    try:
        # 获取用户的类别频率数据
        user_data = topk_counter.get(userid, {})
        cat_data = user_data.get(category, {})
        
        if not cat_data:  # 如果没有数据
            return pd.DataFrame(columns=['venue_id', 'weight'])
        
        freq_df = cat_data['freq'].copy()
        total_num = cat_data['total_num']
        
        if len(freq_df) == 0:  # 如果DataFrame为空
            return pd.DataFrame(columns=['venue_id', 'weight'])
        
        # 计算权重
        freq_df['weight'] = freq_df['freq'] / total_num
        
        # 只保留需要的列并重命名
        result = freq_df[['venue_id', 'weight']].copy()
        
        return result
        
    except Exception as e:
        print(f"Error in recommend_from_topk: {e}")
        return pd.DataFrame(columns=['venue_id', 'weight'])



################# below are old version, useless

## old version of function
'''
def recommend(user_loc, activity, densmap, model='gravity',path = None):
    tag = activity[1]

    if path == None:
        # get parent directory path
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(parent_dir, 'POI_data', tag+'_ca_poi.csv')
    else:
        path = os.path.join(parent_dir,tag+'_ca_poi.csv')


    
    if model == 'gravity':
        dens_matrix = densmap[tag]
        poi_set = pd.read_csv(path)
        
        candidate = compute_weight_gravity(user_loc, dens_matrix, poi_set)
        
        if len(candidate) > 0:
            random_row = candidate.sample(n=1, weights='weight')
            result = random_row['ID'].iloc[0], [random_row['lat'].iloc[0], random_row['lng'].iloc[0]]
        else:
            # 如果没有合适的POI，返回None或者自定义的默认值
            result = None, None
            
        return result
    else:
        return None, None


# def compute_weight_gravity(user_loc, dens_matrix, poi_set,r=10000):
#     # get user index
#     user_idx = (np.array(latlng2meter(densmap.locO,user_loc))//densmap.partitionSize).astype(int)
#     # get maxtix size (need to be inthe range)
#     # input r is the range that the user might consider
#     # different intention might have different r
#     R = int(-((-r)//densmap.partitionSize))
#     center = R//2
#     R = center*2 +1
#     potential = np.zeros((R,R))
#     # generate matrix
#     for i in range(R):
#         for j in range(R):
#             if i == center and j== center:
#                 potential[i,j] = 1
#             else:
#                 potential[i,j] = 1/(np.sqrt(abs(i-center)**2+abs(j-center)**2))**1.5
#     xSize, ySize = dens_matrix.shape

#     ################################################
#     # what if user idx out size of the dens_matrix?
#         # add code here
#     ################################################

#     # user idx inside the matrix
#     flow = densmap.densmap[user_idx[0]-center:user_idx[0]+center+1, user_idx[1]-center:user_idx[1]+center+1]
#     flow = flow*potential
#     # k is ： the top k of grid in map that are consider
#     k = 25
#     # get the top k grid index
#     flattened_flow = flow.flatten()
#     top_k_indices_flat = np.argpartition(flattened_flow, -k)[-k:]
#     top_k_values = flattened_flow[top_k_indices_flat]

#     top_k_indices_2d = np.unravel_index(top_k_indices_flat, flow.shape)
#     # type(top_k_indices_2d)
#     # print("Top K values:\n", top_k_values)
#     # print("Top K indices:\n", top_k_indices_2d)
    
#     # convert top k indices (in flow) to index in the whole matrix
#     top_k_indices_2d = list(top_k_indices_2d)
#     top_k_indices_2d[0] = top_k_indices_2d[0]-center+user_idx[0]
#     top_k_indices_2d[1] = top_k_indices_2d[1]-center+user_idx[1]
#     candidate = poi_set[(poi_set['xIndex'].isin(top_k_indices_2d[0]))&(poi_set['yIndex'].isin(top_k_indices_2d[1]))]
#     candidate = candidate.reset_index(drop=True)


#     # compute the weight using user location
#     candidate['weight'] = candidate.apply(lambda x: calculate_weight(x, densmap.densmap,user_loc), axis=1)
#     candidate['weight'] = candidate['weight']/candidate['weight'].sum()
#     # print(candidate.head(),len(candidate))
#     return candidate


'''
