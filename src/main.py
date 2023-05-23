"""Main entry point for the script

The main function of main_ms takes always three inputs and can take the optional 
input solver. The three needed inputs are the path to the datafile of the model, 
the step length - either an integer in case the step length is always the same 
or a list of two integers, the first indicating the length of the first step and 
the second of the remaining steps - and the path to the folder with the csv files
containing the data for the parameter to varied between scenarios. The solver can 
be indicate in the following way 'solver=gurobi'
"""

import click
import data_split as ds
import itertools
# import main_step as ms
# import new_scen as ns
import os
from pathlib import Path
import pandas as pd
# import results_to_next_step as rtns
import shutil
# import step_to_final as stf
# import subprocess as sp
from typing import Dict, List
import utils
import main_utils as mu

import logging

# logger = logging.getLogger(__name__)
# path_log = os.path.join('results','osemosys_step.log')
path_log = os.path.join('..','results','osemosys_step.log')
logging.basicConfig(filename=path_log, level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--step_length", required=True, multiple=True, 
              help="""
              Provide an integer to indicate the step length, e.g. '5' for 
              five year steps. One can provide the parameter also twice, for 
              example if the first step shall be one year and all following five 
              years one would enter '--step_length 1 --step_length 5'
              """)
@click.option("--input_data", required=True, default= '../data/utopia.txt', 
              help="The path to the input datafile. relative from the src folder, e.g. '../data/utopia.txt'")
@click.option("--solver", default=None, 
              help="If another solver than 'glpk' is desired please indicate the solver. [gurobi]")
@click.option("--cores", default=1, show_default=True, 
              help="Number of cores snakemake is allowed to use.")
@click.option("--path_param", default=None, 
              help="""If the scenario data for the decisions between the steps is 
              saved elsewhere than '../data/scenarios/' on can use this option to 
              indicate the path.
              """)
def main(input_data: str, step_length: int, path_param: str, cores: int, solver=None):
    """Main entry point for workflow"""

    # set up solver logs
    path_sol_logs = os.sep.join(['..','results','solv_logs'])
    try: 
        os.mkdir(path_sol_logs)
    except FileExistsError:
        pass
    
    # Create scenarios folder
    if path_param == None:
        dir_name = os.getcwd()
        path_param = os.path.join(os.sep.join(dir_name.split(os.sep)[:-1]),'data','scenarios')
        
    # format step length 
    step_length = utils.format_step_input(step_length)

    # get step length parameters 
    years_per_step, _ = ds.split_data(input_data, step_length)
    num_steps = len(years_per_step)
    
    # dictionary for steps with new scenarios
    steps = mu.get_step_data(path_param) # returns Dict[int, Dict[str, pd.DataFrame]]
    
    # get option combinations per step
    step_options = mu.get_options_per_step(steps) # returns Dict[int, List[str]]
    step_options = mu.add_missing_steps(step_options, num_steps)
    
    # create option directores in data/
    data_dir = Path("..", "data")
    mu.create_option_directories(str(data_dir), step_options, step_directories=True)
    
    # create option directories in steps/
    step_dir = Path("..", "steps")
    mu.create_option_directories(str(step_dir), step_options, step_directories=True)
    
    # create option directories in results/
    results_dir = Path("..", "results")
    mu.create_option_directories(str(results_dir), step_options, step_directories=False)
    
    # copy over step/scenario/option data
    mu.copy_reference_option_data(src_dir=data_dir, dst_dir=data_dir, options_per_step=step_options)


"""

    # Step length is always the same 
    if len(step_length) < 2:
        
        # modify step data based on each option
        option_data = mu.get_option_data_per_step(steps)
        subdirs = [str(p) for p in data_dir.glob("step*/") if p.is_dir()]
        for subdir in subdirs:
            dirs = mu.split_path_name(subdir)
            if len(dirs) == 1:
                continue
            for dir_num, dir_name in enumerate(dirs):
                if dir_num == 0: # skip root dir 
                    continue
                option = option_data[dir_name] # dir_name will be like A0B1 
                for param in option["PARAMETER"].unique():
                    df_name = Path(*subdirs, param, ".csv")
                    df_ref = pd.read_csv(df_name)
                    option_data_to_apply = option.loc[option["PARAMETER"] == param].reset_index(drop=True)
                    df_new = mu.apply_option(df=df_ref, option=option_data_to_apply)
                    df_new.to_csv(df_name)
                    logger.info(f"Applied {param} option data for {dir_name}")
        
        # solve model 
        if solver != None:
            with open('snakefile_tpl.txt', 'r') as file:
                snakefile = file.readlines()
            line_paths = "PATHS = ['" + "',\n'".join(paths_in_step) + "']\n"

            snakefile[1] = line_paths

            with open('snakefile', 'w') as file:
                file.writelines(snakefile)
            
            cd_snakemake = "snakemake --cores %i" % cores
            sp.run([cd_snakemake], shell=True, capture_output=True)

        else:
            i = 0
            for path_df in paths_df_in_step:
                ms.run_df(path_df,paths_res_in_step[i])
                i+=1

                for sce in range(len(dic_scen_paths[s])):
                    if not os.listdir(paths_res_in_step[sce]): #if scenario run failed, this removes following dependent scnearios
                        for z in range(s+1,len(dic_scen_paths)):
                            for x in range(len(dic_scen_paths[z])):
                                if dic_scen_paths[z][x].split(os.sep)[3] == dic_scen_paths[s][sce].split(os.sep)[-1]:
                                    dic_scen_paths[z][x] = 'none'
                    else:
                        stf.main(paths_res_in_step[sce],dic_fin_res_path[s][sce],s,dic_yr_in_steps[s].iloc[:step_length])

            else:
                dic_fin_res_path[s] = final_paths(dic_scen,dic_fin_res_path[s-1],s)
                copy_fr(s,dic_scen,dic_fin_res_path[s-1])
                i = 0
                for sce in range(len(dic_scen_paths[s-1])):
                    if s in dic_scen:
                        for scn in range(len(dic_scen[s])):
                            if dic_scen_paths[s][i] != 'none':
                                path_dp_d = os.path.join(paths_dp_step[i],'data')
                                rtns.main(path_dp_d,dic_fin_res_path[s-1][sce])
                                ns.main(dic_scen_paths[s][i],s,all_scenarios[s],dic_scen[s][dic_scen_paths[s][i].split(os.sep)[-1]],dic_yr_in_steps)
                                path_df = os.sep.join(paths_dp_step[i].split(os.sep)[:-1])+'.txt'
                                paths_df_in_step.append(path_df)
                                ms.dp_to_df(paths_dp_step[i],path_df)
                                paths_res_in_step.append(dic_step_scen_paths[s][i])
                                paths_in_step.append(os.sep.join(dic_step_scen_paths[s][i].split(os.sep)[2:]))

                            i += 1
                        shutil.rmtree(os.path.join(dic_fin_res_path[s-1][sce],'res'))
                    else:
                        if dic_scen_paths[s][sce] != 'none':
                            path_dp_d = os.path.join(paths_dp_step[sce],'data')
                            rtns.main(path_dp_d,dic_fin_res_path[s-1][sce])
                            path_df = os.sep.join(paths_dp_step[sce].split(os.sep)[:-1])+'.txt'
                            paths_df_in_step.append(path_df)
                            ms.dp_to_df(paths_dp_step[sce],path_df)
                            paths_res_in_step.append(dic_step_scen_paths[s][sce])
                            paths_in_step.append(os.sep.join(dic_step_scen_paths[s][sce].split(os.sep)[2:]))

                logger.info("Paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_in_step})
                logger.info("Result paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_res_in_step})
                if solver != None:
                    with open('snakefile_tpl.txt', 'r') as file:
                        snakefile = file.readlines()
                    line_paths = "PATHS = ['" + "',\n'".join(paths_in_step) + "']\n"

                    snakefile[1] = line_paths

                    with open('snakefile', 'w') as file:
                        file.writelines(snakefile)
                    
                    cd_snakemake = "snakemake --cores %i" % cores
                    sp.run([cd_snakemake], shell=True, capture_output=True)

                else:
                    i = 0
                    for path_df in paths_df_in_step:
                        ms.run_df(path_df,paths_res_in_step[i])
                        i+=1
                for sce in range(len(paths_res_in_step)):
                    if not os.listdir(paths_res_in_step[sce]):
                        p = len(dic_scen_paths[s][sce].split(os.sep))-1
                        for z in range(s+1,len(dic_scen_paths)):
                            for x in range(len(dic_scen_paths[z])):
                                if dic_scen_paths[z][x]!='none':
                                    if dic_scen_paths[z][x].split(os.sep)[p] == dic_scen_paths[s][sce].split(os.sep)[-1]:
                                        dic_scen_paths[z][x] = 'none'
                    else:
                        stf.main(paths_res_in_step[sce],dic_fin_res_path[s][sce],s,dic_yr_in_steps[s].iloc[:step_length])

    else:
        # Procedure if the first step has a different length than the following steps.
        step_length_tp = step_length
        step_length = []
        for l in step_length_tp:
            step_length.append(int(l))
        dic_yr_in_steps, full_steps = ds.split_data(input_data,step_length)
        all_steps = len(dic_yr_in_steps)
        all_scenarios = get_scen(path_param) #Create dictionary for stages with decisions creating new scenarios
        dic_step_paths = step_directories(os.path.join('..','data'),all_steps)
        dic_scen = scen_dic(all_scenarios,all_steps)
        dic_scen_paths = scen_directories(dic_step_paths,dic_scen)
        dic_step_res_paths = step_directories(os.path.join('..','steps'),all_steps)
        dic_step_scen_paths = scen_directories(dic_step_res_paths,dic_scen)
        dic_fin_res_path = dict()
        for s in range(all_steps):
            logger.info('Step %i started' % s)
            paths_dp_step = copy_dps(s,dic_scen,dic_scen_paths)
            paths_in_step = []
            paths_df_in_step = []
            paths_res_in_step = []
            if s==0:
                dic_fin_res_path[s] = final_paths(dic_scen,[],s)
                for sce in range(len(dic_scen_paths[s])):
                    if dic_scen_paths[s][sce] != 'none':
                        if s in dic_scen:
                            ns.main(dic_scen_paths[s][sce],s,all_scenarios[s],dic_scen[s][dic_scen_paths[s][sce].split(os.sep)[-1]],dic_yr_in_steps)
                        path_df = os.sep.join(paths_dp_step[sce].split(os.sep)[:-1])+'.txt'
                        paths_df_in_step.append(path_df)
                        ms.dp_to_df(paths_dp_step[sce],path_df)
                        paths_res_in_step.append(dic_step_scen_paths[s][sce])
                        paths_in_step.append(os.sep.join(dic_step_scen_paths[s][sce].split(os.sep)[2:]))

                logger.info("Paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_in_step})
                logger.info("Result paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_res_in_step})
                if solver!=None:
                    with open('snakefile_tpl.txt', 'r') as file:
                        snakefile = file.readlines()
                    line_paths = "PATHS = ['" + "',\n'".join(paths_in_step) + "']\n"

                    snakefile[1] = line_paths

                    with open('snakefile', 'w') as file:
                        file.writelines(snakefile)
                    
                    cd_snakemake = "snakemake --cores %i" % cores
                    sp.run([cd_snakemake], shell=True, capture_output=True)

                else:
                    i = 0
                    for path_df in paths_df_in_step:
                        ms.run_df(path_df,paths_res_in_step[i])
                        i+=1

                for sce in range(len(dic_scen_paths[s])):
                    if not os.listdir(paths_res_in_step[sce]): #if scenario run failed, this removes following dependent scnearios
                        for z in range(s+1,len(dic_scen_paths)):
                            for x in range(len(dic_scen_paths[z])):
                                if dic_scen_paths[z][x].split(os.sep)[3] == dic_scen_paths[s][sce].split(os.sep)[-1]:
                                    dic_scen_paths[z][x] = 'none'
                    else:
                        stf.main(paths_res_in_step[sce],dic_fin_res_path[s][sce],s,dic_yr_in_steps[s].iloc[:step_length[0]])

            else:
                dic_fin_res_path[s] = final_paths(dic_scen,dic_fin_res_path[s-1],s)
                copy_fr(s,dic_scen,dic_fin_res_path[s-1])
                i = 0
                for sce in range(len(dic_scen_paths[s-1])):
                    if s in dic_scen:
                        for scn in range(len(dic_scen[s])):
                            if dic_scen_paths[s][i] != 'none':
                                path_dp_d = os.path.join(paths_dp_step[i],'data')
                                rtns.main(path_dp_d,dic_fin_res_path[s-1][sce])
                                ns.main(dic_scen_paths[s][i],s,all_scenarios[s],dic_scen[s][dic_scen_paths[s][i].split(os.sep)[-1]],dic_yr_in_steps)
                                path_df = os.sep.join(paths_dp_step[i].split(os.sep)[:-1])+'.txt'
                                paths_df_in_step.append(path_df)
                                ms.dp_to_df(paths_dp_step[i],path_df)
                                paths_res_in_step.append(dic_step_scen_paths[s][i])
                                paths_in_step.append(os.sep.join(dic_step_scen_paths[s][i].split(os.sep)[2:]))

                            i += 1
                        shutil.rmtree(os.path.join(dic_fin_res_path[s-1][sce],'res'))
                    else:
                        if dic_scen_paths[s][sce] != 'none':
                            path_dp_d = os.path.join(paths_dp_step[sce],'data')
                            rtns.main(path_dp_d,dic_fin_res_path[s-1][sce])
                            path_df = os.sep.join(paths_dp_step[sce].split(os.sep)[:-1])+'.txt'
                            paths_df_in_step.append(path_df)
                            ms.dp_to_df(paths_dp_step[sce],path_df)
                            paths_res_in_step.append(dic_step_scen_paths[s][sce])
                            paths_in_step.append(os.sep.join(dic_step_scen_paths[s][sce].split(os.sep)[2:]))

                logger.info("Paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_in_step})
                logger.info("Result paths in step %(step)i: %(paths)s" % {'step': s, 'paths': paths_res_in_step})
                if solver!=None:
                    with open('snakefile_tpl.txt', 'r') as file:
                        snakefile = file.readlines()
                    line_paths = "PATHS = ['" + "',\n'".join(paths_in_step) + "']\n"

                    snakefile[1] = line_paths

                    with open('snakefile', 'w') as file:
                        file.writelines(snakefile)
                    
                    cd_snakemake = "snakemake --cores %i" % cores
                    sp.run([cd_snakemake], shell=True, capture_output=True)

                else:
                    i = 0
                    for path_df in paths_df_in_step:
                        ms.run_df(path_df,paths_res_in_step[i])
                        i += 1
                for sce in range(len(paths_res_in_step)):
                    if not os.listdir(paths_res_in_step[sce]):
                        p = len(dic_scen_paths[s][sce].split(os.sep))-1
                        for z in range(s+1,len(dic_scen_paths)):
                            for x in range(len(dic_scen_paths[z])):
                                if dic_scen_paths[z][x]!='none':
                                    if dic_scen_paths[z][x].split(os.sep)[p] == dic_scen_paths[s][sce].split(os.sep)[-1]:
                                        dic_scen_paths[z][x] = 'none'
                    else:
                        stf.main(paths_res_in_step[sce],dic_fin_res_path[s][sce],s,dic_yr_in_steps[s].iloc[:step_length[1]])


"""

if __name__ == '__main__':
    main() #input_data,step_length,path_param,solver)
