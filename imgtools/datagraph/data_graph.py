from multiprocessing import Value
import pandas as pd
import os
import numpy as np
from functools import reduce
import time
from tqdm import tqdm
from functools import reduce

class DataGraph:
    '''
    This class given the crawled dataset in the form of CSV file, deals with forming a graph on the full dataset, taking advantage of connections between different modalities. Based
    on these connections, an edge table is made. This class also supports querying and for a given query, returns the file locations of the user-specified sub-dataset from the full dataset.
    The graph is made based on the references made by different DICOMS. Different connections are given different edge type values, to make parsing easier. The edge types are as follows:-
    1) edge_type:0 RTDOSE(key:ref_rt) -> RTSTRUCT(pair: series/instance)
    2) edge_type:1 RTDOSE(key:ref_ct) -> CT(pair: series) 
    3) edge_type:2 RTSTRUCT(key:ref_ct) -> CT(pair: series) 
    4) edge_type:3 RTSTRUCT(key:ref_ct) -> PT(pair: series) 
    5) edge_type:4 CT(key:study) -> PT(pair: study) 

    Once the edge table is formed, one can query on the graph to get the desired results. For uniformity, the supported query is list of modalities to consider
    For ex:
    query = ["CT","RTDOSE","RTSTRUCT","PT], will return interconnected studies containing the listed DICOM modalities. The interconnected studies for example may look like 
    (RTDOSE->RTSTRUCT->CT<-PT<-RTSTRUCT)
    '''
    def __init__(self,path_crawl:str,edge_file=False,edge_path="./patient_id_full_edges.csv") -> None:
        '''
        path_crawl : The csv returned by the crawler
        edge_file: Whether a graph should be made or a pre-existing graph can be used
        edge_path: This path denotes where the graph in the form of edge table is stored or to be stored
        '''
        self.df = pd.read_csv(path_crawl,index_col=0)
        self.edge_path = edge_path
        if edge_file==False:
            self.form_graph()
        else:
            self.df_edges = pd.read_csv(self.edge_path)
    
    def form_graph(self):
        '''
        Forms edge table based on the crawled data
        '''
        #Remove entries with no RT dose reference (Temporary)
        df_filter = self.df.loc[~((self.df["modality"]=="RTDOSE") & (self.df["reference_ct"].isna()) & (self.df["reference_rs"].isna()))]

        #Get all study ids
        all_study= df_filter.study.unique()
        start = time.time()

        #Defining Master DF to store all the Edge dataframes
        self.DF_master = []

        for i in tqdm(range(len(all_study))):
            self._form_edge_study(df_filter,all_study,i)

        # df_edge_patient = form_edge_study(df,all_study,i)
        end = time.time()
        print("\nTotal time taken: {}".format(end-start))

        self.df_edges = pd.concat(self.DF_master, axis=0, ignore_index=True)
        self.df_edges.loc[self.df_edges.study_x.isna(),"study_x"] = self.df_edges.loc[self.df_edges.study_x.isna(),"study"]
        #dropping some columns
        self.df_edges.drop(columns=["study_y","patient_ID_y","series_description_y","study_description_y","study"],inplace=True)
        self.df_edges.sort_values(by="patient_ID_x",ascending=True)
        print("Saving edge table in {}".format(self.edge_path))
        self.df_edges.to_csv(self.edge_path,index=False)

    def _form_edge_study(self,df,all_study,study_id):
        '''
        For a given study id forms edge table
        '''
        
        df_study = df.loc[self.df["study"]==all_study[study_id]]
        DF_list = []
        
        #Bifurcating the dataframe
        dose = df_study.loc[df_study["modality"]=="RTDOSE"]
        struct = df_study.loc[df_study["modality"]=="RTSTRUCT"]
        ct = df_study.loc[df_study["modality"]=="CT"]
        pet = df_study.loc[df_study["modality"]=="PT"]

        edge_types = np.arange(5)
        for edges in edge_types:
            if edges==0:
                #FORMS RTDOSE->RTSTRUCT, can be formed on both series and instance uid
                df_comb1 = pd.merge(struct,dose,left_on="instance_uid",right_on="reference_rs")
                df_comb2 = pd.merge(struct,dose,left_on="series",right_on="reference_rs")
                df_combined = pd.concat([df_comb1,df_comb2])
                #Cases where both series and instance_uid are the same for struct
                df_combined.drop_duplicates(subset=["instance_uid_x"],inplace=True)

            elif edges==1:
                #FORMS RTDOSE->CT 
                df_combined = pd.merge(ct,dose,left_on="series",right_on="reference_ct")

            elif edges==2:
                #FORMS RTSTRUCT->CT on ref_ct to series
                df_combined = pd.merge(ct,struct,left_on="series",right_on="reference_ct")

            elif edges==3:
                # FORMS RTSTRUCT->PET on ref_ct to series
                df_combined = pd.merge(pet,struct,left_on="series",right_on="reference_ct")

            else:
                # FORMS PET->CT on study
                df_combined = pd.merge(ct,pet,left_on="study",right_on="study")
            
            df_combined["edge_type"]=edges
            DF_list.append(df_combined)
                
        DF_edges = pd.concat(DF_list, axis=0, ignore_index=True)
        self.DF_master.append(DF_edges)
    
    def parser(self,query_string:str)->pd.DataFrame:
        '''
        For a given query string(Check the documentation), returns the dataframe consisting of two columns namely modality and folder location of the connected nodes
        Parameters:
            df: Dataframe consisting of the crawled data
            df_edges: Processed Dataframe forming a graph, stored in the form of edge table
            query_string: Query string based on which dataset will be formed
        
        Query ideas:
        There are four basic supported modalities are RTDOSE, RTSTRUCT, CT, PT
        The options are:
        1) RTDOSE
        2) RTSTRUCT
        3) CT
        4) PT
        5) RTDOSE,RTSTRUCT,CT
        6) CT,PT
        7) CT,RTSTRUCT
        '''
        #Basic processing of just one modality
        supp_mods = ["RTDOSE","RTSTRUCT","CT","PT"]
        edge_def = {"RTSTRUCT,RTDOSE":0,"CT,RTDOSE":1,"CT,RTSTRUCT":2,"PET,RTSTRUCT":3,"CT,PET":4}
        self.mods= query_string.split(",")

        if query_string in supp_mods:
            final_df = self.df.loc[self.df.modality==query_string,"folder"].to_frame()
            final_df.rename(columns = {"folder":"folder_{}".format(query_string)},inplace=True)
        
        elif len(self.mods)==2:
            #Reverse the query string
            query_string_rev = (",").join(self.mods[::-1])
            if query_string in edge_def.keys():
                edge_type = edge_def[query_string]
                valid = query_string
            elif query_string_rev in edge_def.keys():
                edge_type = edge_def[query_string_rev]
                valid = query_string_rev
            else:
                raise ValueError("Invalid Query. Select valid pairs ")
            final_df = self.df_edges.loc[self.df_edges.edge_type==edge_type,["folder_x","folder_y"]]
            node_dest = valid.split(",")[0]
            node_origin = valid.split(",")[1]
            final_df.rename(columns={"folder_x":"folder_{}".format(node_dest),"folder_y":"folder_{}".format(node_origin)},inplace=True)

        elif len(self.mods)>2:
            #Form aggregates for easier parsing, gets the edge types for each study and aggregates as a string. This way one can do regex based on what type of subgraph the user wants
            df_new = self.df_edges.groupby("study_x").agg({'edge_type':self.list_edges})
            df_new.reset_index(level=0, inplace=True)
            df_new["edge_type"] = df_new["edge_type"].astype(str)
        
            #Processing of combinations of modality
            if ("CT" in query_string) & ("RTSTRUCT" in query_string) & ("RTDOSE" in query_string) & ("PT" not in query_string):
                #Fetch the required data. Checks whether each study has edge 2 and (edge 1 or edge 0)
                relevant_studyid = df_new.loc[(df_new.edge_type.str.contains('(?=.*(1|0))(?=.*2)')),"study_x"].unique()
                #Based on the correct study ids, fetches are the relevant edges
                df_processed = self.df_edges.loc[self.df_edges.study_x.isin(relevant_studyid) & (self.df_edges.edge_type.isin([0,1,2]))]
                # final_df = get_df(df_processed,query_string,relevant_studyid)
                final_df = self._get_df(df_processed,relevant_studyid)

            elif ("CT" in query_string) & ("RTSTRUCT" in query_string) & ("RTDOSE" in query_string) & ("PT" in query_string):
                #Fetch the required data. Checks whether each study has edge 2,3,4 and (edge 1 or edge 0)
                relevant_studyid = df_new.loc[(df_new.edge_type.str.contains('(?=.*(1|0))(?=.*2)(?=.*3)(?=.*4)')),"study_x"].unique()
                #Based on the correct study ids, fetches are the relevant edges
                df_processed = self.df_edges.loc[self.df_edges.study_x.isin(relevant_studyid) & (self.df_edges.edge_type.isin([0,1,2,3,4]))]
                # final_df = get_df(df_processed,query_string,relevant_studyid)
                final_df = self._get_df(df_processed,relevant_studyid)

            elif ("CT" in query_string) & ("RTSTRUCT" in query_string) & ("PT" in query_string) & ("RTDOSE" not in query_string):
                #Fetch the required data. Checks whether each study has edge 2,3,4 and (edge 1 or edge 0)
                relevant_studyid = df_new.loc[(df_new.edge_type.str.contains('(?=.*2)(?=.*3)(?=.*4)')),"study_x"].unique()
                #Based on the correct study ids, fetches are the relevant edges
                df_processed = self.df_edges.loc[self.df_edges.study_x.isin(relevant_studyid) & (self.df_edges.edge_type.isin([2,3,4]))]
                # final_df = get_df(df_processed,query_string,relevant_studyid)
                final_df = self._get_df(df_processed,relevant_studyid)
            
            else:
                raise ValueError("Please enter the correct query")
        else:
            raise ValueError("Please enter the correct query")
        return final_df
    
    def _get_df(self,df_edges_processed,rel_studyids):
        '''
        Assumption: The components are determined based on the unique CTs. Please ensure the data conforms to this case. From the analysis, there are no cases where CT and PT are present but are disconnected
        Hence this assumption should hold for most of the cases
        This function returns dataframe consisting of folder location and modality for subgraphs
        Parameters:
            df_edges_processed: Dataframe processed containing only the desired edges from the full graph
        '''
        #Storing all the components across all the studies
        self.final_dict = []
        final_df = []
        #Determine the number of components
        for i in range(len(rel_studyids)):
            df_temp = df_edges_processed.loc[df_edges_processed.study_x==rel_studyids[i]]
            CT_locs = df_temp.loc[df_temp.modality_x=="CT"]
            comp = CT_locs.series_x.unique()
            A = []
            save_folder_comp = []
            #Initialization. For each component intilize a dictionary with the CTs and their connections
            for j in range(len(comp)):
                #For each component, this loop stores the CT and its connections
                temp = {}
                #For saving the components in a format easier for the main pipeline
                folder_save = {}
                temp["study"] = rel_studyids[i]
                temp[comp[j]] = {}
                temp[comp[j]]["modality"] = "CT"
                df_connections = CT_locs.loc[CT_locs.series_x==comp[j]]
                temp[comp[j]]["folder"] = df_connections["folder_x"].iloc[0]
                folder_save["folder_{}".format("CT")] = df_connections["folder_x"].iloc[0]
                temp_dfconn = df_connections[["series_y","modality_y","folder_y"]]
                for k in range(len(temp_dfconn)):
                    #This loop stores connection of the CT
                    temp[temp_dfconn.iloc[k,0]] = {}
                    temp[temp_dfconn.iloc[k,0]]["modality"] = temp_dfconn.iloc[k,1]
                    temp[temp_dfconn.iloc[k,0]]["folder"] = temp_dfconn.iloc[k,2]
                    temp[temp_dfconn.iloc[k,0]]["conn_to"] = "CT"
                    folder_save["folder_{}_CT".format(temp_dfconn.iloc[k,1])] = temp_dfconn.iloc[k,2]
                A.append(temp)
                save_folder_comp.append(folder_save)
            #For rest of the edges left out, the connections are formed by going through the dictionary. For cases such as RTstruct-RTDose and PET-RTstruct
            Rest_locs = df_temp.loc[df_temp.modality_x!="CT",["series_x","modality_x","folder_x","series_y","modality_y","folder_y"]]
            
            flag = 0
            for j in range(len(Rest_locs)):
                for k in range(len(comp)):
                    if Rest_locs.iloc[j,0] in A[k]:
                        A[k][Rest_locs.iloc[j,3]] = {}
                        A[k][Rest_locs.iloc[j,3]]["modality"] = Rest_locs.iloc[j,4]
                        A[k][Rest_locs.iloc[j,3]]["folder"] = Rest_locs.iloc[j,5]
                        A[k][Rest_locs.iloc[j,3]]["conn_to"] = Rest_locs.iloc[j,1]
                        if Rest_locs.iloc[j,4]=="RTDOSE":
                            #RTDOSE is connected via either RTstruct or CT, but we usually don't care
                            save_folder_comp[k]["folder_{}_CT".format(Rest_locs.iloc[j,4])] = Rest_locs.iloc[j,5]
                        else:
                            key = "folder_{}_{}".format(Rest_locs.iloc[j,4],Rest_locs.iloc[j,1])
                            #if there is already a connection and one more same category modality wants to connect
                            if key in save_folder_comp[k].keys():
                                key = key + "_1"
                            save_folder_comp[k][key] = Rest_locs.iloc[j,5]
                        flag = 0
                    else:
                        flag = 1
            if flag==1:
                raise ValueError("In studyID: {}, one of the edges had no match to any of the components. Please check the data".format(rel_studyids[i]))

            #Check if the number of nodes in a components isn't less than the query nodes, if yes then remove that component
            save_folder_comp = [save_folder_comp[j] for j in range(len(comp)) if len(A[j].keys())>=len(self.mods)+1]         
            A = [items for items in A if len(items.keys())>=len(self.mods)+1]

            self.final_dict = self.final_dict + A
            final_df = final_df + save_folder_comp
        final_df = pd.DataFrame(final_df)
        return final_df
    
    @staticmethod
    def list_edges(series):
        return reduce(lambda x,y:str(x)+str(y),series)

if __name__=="__main__":
    graph = DataGraph(path_crawl="/Users/bhaibeka/Vishwesh/imgtools_Head-Neck-PET-CT_2.csv",edge_file=True,edge_path="/Users/bhaibeka/Vishwesh/patient_id_full_edges.csv")
    # graph = DataGraph(path_crawl="./imgtools_Head-Neck-PET-CT_2.csv",edge_file=False,edge_path="./patient_id_full_edges2.csv")
    # final_df = graph.parser("CT,RTSTRUCT,RTDOSE,PT")
    final_df = graph.parser("RTSTRUCT,CT,PT")
    # final_df = graph.parser("CT,RTSTRUCT,RTDOSE")
    