import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_distances
from sklearn.neighbors import NearestNeighbors
import pickle
from scipy.sparse import csr_matrix


##########################################
# 크롤링한 데이터 mysql 에서 가지고오기
##########################################
password = ''
engine = create_engine(f'mysql+pymysql://root:{password}@localhost/movie?charset=utf8')
connect = engine.connect()
raw_data_set = pd.read_sql_table('movie', connect)
# print(raw_data_set)





##########################################
# 평점이 1개여서 user a와 유사한 b,c,d중 b만 평가한 영화 z에 대해서 b가 10점을 주면 a에게 무조건 추천을 하게 됨
# 이를 방지하고자 5번이상 평가된 영화만 넣도록 함
##########################################
def Remove_5_under_movie(data):
    title_num_ = data.groupby('title').count().sort_values('user')
    # print(title_num_)
    title_under_5 = title_num_[title_num_.user <= 5]
    # print(title_under_10)
    title_under_5_list = list(title_under_5.index)
    for title in title_under_5_list:
        data = data[data['title'] != title]
    return data

raw_data_set = Remove_5_under_movie(raw_data_set)
# print(raw_data_set)





##########################################
# 데이터 베이스에 넣기 위해 만든 PK id는 삭제
##########################################
data = raw_data_set
data = data.drop(['id'], axis = 1)
#print(data)





##########################################
# 데이터 파악
##########################################

#  상위 이용 정리
print('=================================================================================================================================================')
user_top_5 = data.user.value_counts()[:5]
print(user_top_5)
# movie_top_5 = data.title.value_counts()[:5]
#print(movie_top_5)



#########################################
# Colaborative Filtering
# data set 행렬로 만들기
#########################################
# 라벨링
def labeling(column_name):
    le = LabelEncoder()
    data_copy = data.copy()
    temp_data = le.fit_transform(data_copy[column_name])
    data_label = pd.DataFrame(temp_data, columns = [column_name+'_label'], index=data_copy.index)
    # print(labeling_data)
    return data_label

label_data_user = labeling('user')
label_data_title = labeling('title')
#print(label_data_user)

temp_1 = data.copy()
temp_1 = temp_1.drop(temp_1.columns[0], axis=1)
label_data_set = pd.concat([label_data_user, label_data_title, temp_1], axis=1)
# print(label_data_set)

movie_list = list(data.title.unique())
movie_list = sorted(movie_list, key= str)
# print(movie_list)
data_matrix = pd.DataFrame(columns=['user'] + movie_list)
# print(data_matrix)
# Columns: [user, #살아있다, 0.0MHz, 007 노 타임 투 다이, 12 몽키즈, ...]

user_num = len(label_data_set['user_label'].unique())
movie_num = len(label_data_set['title_label'].unique())
user_score_list = []
for num in range(user_num):
    user_score_list = [0 for i in range(movie_num)]
    temp_2 = label_data_set[label_data_set['user_label'] == num]
    for j in temp_2.index:
        user_score_list[temp_2.loc[j]['title_label']] = temp_2.loc[j]['score']
    data_matrix.loc[num] = [num] + user_score_list
# print(data_matrix)
# 행 : user 별 평가 점수
# 열 : 영화 별 평가 점수
#     user #살아있다 0.0MHz 007 노 타임 투 다이 12 몽키즈  ... 호텔 뭄바이 혼자 사는 사람들 화이트데이: 부서진 결계 회사원 히트맨
#  0    0     0      0             0      0  ...      0         0             0   0   0

# pickling
# user name을 data_matrix에 추가한 final_matrix 완성
file = data_matrix
dir = open('pickling/utilitymatrix', 'wb')
pickle.dump(file, dir)
dir.close()
user_name_ = list(data['user'].unique())
user_name_ = sorted(user_name_, key=str)
user_name_ = pd.DataFrame(user_name_)
user_name_.columns = ['user_name']
dir_user = open('pickling/user_name', 'wb')
pickle.dump(user_name_, dir_user)
dir_user.close()
f1 = open('pickling/utilitymatrix', 'rb')
temp_matrix = pickle.load(f1)
data_matrix = temp_matrix
# print(data_matrix)
f2 = open('pickling/user_name', 'rb')
user_ = pickle.load(f2)
final_matrix = pd.concat([user_, data_matrix], axis=1)
print('=================================================================================================================================================')
print(final_matrix)




#############################################
# 코사인 우사도 적용
#############################################
def cosine_similarity(data):
    similarity = 1 - cosine_distances(data)
    return similarity

#cos_sim = cosine_similarity(data_matrix)
#print(cos_sim)

# 유사한 사람 찾기
# 코사인 유사도 정렬해서 앞에서 가져오는게 날듯 수정 필요
class Find(object):
    def __init__(self, user_name, neigh_num):
        self.user_name = user_name
        self.neigh_num = neigh_num

    def name_to_num(self):
        user_name_list = list(final_matrix['user_name'].unique())
        user_num_infind =0
        for i in range(len(user_name_list)):
            if user_name_list[i] == self.user_name:
                user_num_infind = i
                break
        return user_num_infind

    #알고리즘을 이용한 이웃검색
    def find_near_neigh(self):
        ################################ cosine similarity ######################################
        user_num_infind = Find.name_to_num(self)
        KNN = NearestNeighbors(n_neighbors=self.neigh_num, metric='cosine')
        KNN.fit(data_matrix)

        similars = {}
        similar_distance, similars_user = KNN.kneighbors(data_matrix)
        similar_distance = similar_distance[user_num_infind][1:]
        similars['sim_distance'] = similar_distance

        similars_user = similars_user[user_num_infind][1:]
        similars['sim_user'] = list(similars_user)
        # print(similars)
        return similars

    def neigh_narray(self):
        similar = Find.find_near_neigh(self)
        similar_user_list = similar['sim_user']

        columns = list(data_matrix.columns)
        df = pd.DataFrame(columns=columns)

        for i in range(len(similar_user_list)):
            neighbor_df = data_matrix[data_matrix['user'] == similar_user_list[i]]
            neighbor_df = pd.concat([df, neighbor_df])
            df = neighbor_df

        narray = df.values
        narray = narray[:, 1:]
        return narray

# user_neighbor = Find('mks1', 10)
# print(user_neighbor.find_near_neigh())


class Calculate_rating(Find):
    def __init__(self, user_name, neigh_num):
        Find.__init__(self, user_name, neigh_num)

    def calcul_rating(self):
        narray = Find.neigh_narray(self)
        similar = Find.find_near_neigh(self)
        similar_diatance = similar['sim_distance']

        rating_list = []
        #영화 수만큼
        ###################################### 알고리즘 적용부분 ##################################
        for colnum in range(narray.shape[1]):
            sum_ = 0
            rating = 0
            sum_distance = 0
            for i in range(0, len(narray[:, colnum])):
                sum_ += float(narray[:, colnum][i]) * float(similar_diatance[i])
                if narray[:, colnum][i] != 0:
                    sum_distance += similar_diatance[i]
            if sum_distance == 0:
                rating = 0
            else:
                rating = sum_ / sum_distance
            # print(sum_, sum_distance,rating)

            if rating<0:
                rating = 0
            elif rating>10:
                rating = 10
            else:
                rating = int(rating)

            rating_list.append(rating)
        return rating_list

    def original_rating_list(self):
        user_num = Find.name_to_num(self)

        target_df = data_matrix[data_matrix['user'] == user_num]
        target_narray = target_df.values
        target_narray = target_narray[:, 1:]

        target_user_rating = []
        for i in range(target_narray.shape[1]):
            value = int(target_narray[0][i])
            target_user_rating.append(value)
        return target_user_rating

#user_dis = Calculate_rating('mks1', 10)
#print(csr_matrix(user_dis.calcul_rating()))
#print(user_dis.calcul_rating())


class CF(Calculate_rating):
    def __init__(self, user_name, neigh_num):
        Find.__init__(self, user_name, neigh_num)
        Calculate_rating.__init__(self, user_name, neigh_num)

    def recommend_movie_list(self):
        user_num = Find.name_to_num(self)
        calcul_list = Calculate_rating.calcul_rating(self)
        origin_list = Calculate_rating.original_rating_list(self)
        all_movie_list = list(data_matrix)[1:]
        temp_list = []

        for k in range(len(calcul_list)):
            if int(origin_list[k]) != 0:
                temp_list.append(0)
            else:
                temp_list.append(int(calcul_list[k]))

        recommend_list_index = []
        for k in range(len(temp_list)):
            ################################################예측 평가 점수 부분
            if temp_list[k] >= 8:
                recommend_list_index.append(k)

        recommend_list_str = []
        for k in recommend_list_index:
            recommend_list_str.append(all_movie_list[k])

        already_rating_movie = [k for k in range(len(temp_list)) if temp_list[k] == 0]
        user_movie_list = [all_movie_list[k] for k in range(len(all_movie_list)) if k not in already_rating_movie]
        final_dict = {}
        final_dict['by_rating'] = recommend_list_str
        final_dict['by_delete'] = user_movie_list
        return final_dict

    def recommendation(self):
        user_number = Find.name_to_num(self)
        movie_dict = CF.recommend_movie_list(self)
        by_rating_list = movie_dict['by_rating']
        by_delete_list = movie_dict['by_delete']

        if len(by_rating_list) <2:
            recommendation_file = by_delete_list
        else:
            recommendation_file = by_rating_list

        #user_name = final_matrix['user_name'][user_number]
        return recommendation_file
