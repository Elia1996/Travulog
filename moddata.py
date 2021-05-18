#!/usr/bin/python3
import sys
import os
import re
import json

#  RemoveComments(string):
#  GetBits(string):
#  GetParamBase(name_or_list):
#  CreateBitsDefinition(bits_dict, signal_type=""):
#  moddata class

#     __init__(sf, filename = "", module_prefix="", indent="        "):
#     SetVerilogBlock(sf, verilog_block):
#     SetModuleName(sf, module_name):
#     SetInputPortConnections(sf, input_port_connection_list):
#     SetInputDiffPortConnections(sf, input_diff_port_connection_list):
#     SetOutputPortConnections(sf, output_port_connection_list):
#     SetOutputDiffPortConnections(sf, output_diff_port_connection_list):
#     SetParameterConnections(sf, parameter_connection_list):
#     SetSigAsAnotherModuleSig(sf, other_module, signals_name_list, new_sig_type):
#           Dato l'oggetto moddata di un modulo (other_module), la lista dei segnali (signals_name_list)
#           e la tipologia dei segnali dati nella lista (new_sig_type) ossia se è la lista dei segnali
#           di ingresso, di uscita o dei parametri, viene verificato che esistano i segnali della lista nel blocco 
#           other_module e, se esistono, vengono copiate le loro caratteristiche nell'oggetto moddata corrente.
#           Questa funzione viene usata per creare un sotto modulo da un blocco di codice verilog all'interno 
#           del modulo other_module
#     SetInternSigFromOtherModuleSearchingInVerilogCode(sf, other_module):
#           Una volta utilizzata la funzione SetSigAsAnotherModuleSig manca l'assegnazione dei segnali interni del modulo
#           per sapere quali segnali inizializzare si prendono in esame tutti i segnali di other_module e, una volta 
#           esclusi quelli di io già usati, si cercano tutti gli altri nel blocco di verilog del blocco corrente
#           se un segnale viene trovato, viene copiato da other_module e settato come interno nel nuovo blocco.
#     Analyze(sf, moddata_similar=0): 
#           Legge il file passato in __init__ e estrapola le proprietà del modulo verilog
#
#     GetModuleName(sf):
#     GetParameterNamesList(sf):
#     GetParameterBitsList(sf):
#     GetParameterValuesList(sf):
#     GetInputSigNamesList(sf):
#     GetInputSigBitsList(sf):
#     GetInputSigDiffNamesList(sf):
#     GetInputSigDiffBitsList(sf):
#     GetOutputSigNamesList(sf):
#     GetOutputSigBitsList(sf):
#     GetOutputSigDiffNamesList(sf):
#     GetOutputSigDiffBitsList(sf):
#     GetInternSigNamesList(sf):
#     GetInternSigBitsList(sf):
#     GetAllIoSigName(sf):
#     GetAllSigName(sf):
#     GetSigData(sf, signal_name):
#     GetVerilogBlock(sf):
#     GetIndent(sf, indent_level=1):
#     GetModuleNameNoPrefix(sf):
#     GetIndent(sf, indent_level=1):
#     GetModuleNameNoPrefix(sf):
#     GetParamBase(sf):
#     GetParamBaseNoPrefix(sf):
#     GetPortIoFromList(sf, sig_name_list, ending=False, change_bit=False, indent_level=1):
#     GetParameterDeclaration(sf,indent_level=0):
#     GetDeclaration(sf, indent_level=0, change_bit_all_io_and_intern_sig = False):
#     GetCompleteVerilog(sf):
#           Ritorna il verilog completo del modulo considerando le modifiche effettuate 
#
#     GetInstance(sf, inst_name, indent_level=1):
#           Ritorna un'instanza del modulo 
#
#     SigExist(sf, signal_name):
#     VerilogBlockExist(sf):


def RemoveComments(string):
    # remove all occurrences streamed comments (/*COMMENT */) from string
    string = re.sub(re.compile("/\*.*?\*/",re.DOTALL ) ,"" ,string)
    # remove all occurrence single-line comments (//COMMENT\n ) from string
    string = re.sub(re.compile("//.*?\n" ) ,"" ,string)
    string = re.sub(re.compile("//.*" ) ,"" ,string)
    return string

def GetBits(string):
    ####################################################################################
    # Find bits from a sv init string
    ####################################################################################
    if "[" in string:
        lista = string.split(":")
        if len(lista) == 2:
            return {"N0UP":lista[0].split("[")[-1], "N0DW":"0", "N1UP":"0", "N1DW":"0" }
        elif len(lista) == 3:
            return {"N1UP":lista[0].split("[")[-1], "N1DW":"0" ,"N0UP":lista[1].split("[")[-1],"N0DW":"0" }
        else:
            print("ERROR in GetBits, more then two dimension not are supported")
            exit(-1)
    else:
        return {"N0UP":"0", "N0DW":"0" ,"N1UP":"0", "N1DW":"0"}


def GetParamBase(name_or_list):
    """ This function take a name of this type:
      1word_2word_3word_ etc...
      and return a string like this (N=2):
           1W2W3W etc...
      So create a sort of identifier of the name using the first N letter of each
      word
    """
    N=2 # letter from each word
    if type(name_or_list)==list:
        name = name_or_list["module"]
    else:
        name = name_or_list
    param_name=name[:N].upper()
    i=N
    while i < len(name):
        if name[i] == "_":
            i+=1
            param_name += name[i:i+N].upper()
            i+=N
        else:
            i+=1

    return param_name

def CreateBitsDefinition(bits_dict, signal_type=""):
    """ return a string with signal bits delcaration
    For example if bits_dict={"N0UP":3,"N0DW":0, "N1UP":4,"N1DW"=0}
    and signal_type="logic", the function will return
        "logic [4:0][3:0]"
    """
    if type(bits_dict) != dict:
        print("ERROR in CreateBitsDefinition, bits_dict should be a list")
        exit(-1)
    
    element_list=[]

    for key in bits_dict.keys():
        # only N0 and N1 supported at the moment
        if key != "N0UP" and key!="N0DW" and key!="N1UP" and key!="N1DW":
            print("ERROR in  CreateBitsDefinition, key in bits_dict not suppoted (%s)" % key)
            exit(-1)
        element_list.append(key)
    
    # Now the order will be ['N0DW', 'N0UP', 'N1DW', 'N1UP']
    if "N0UP" in element_list and not "N0DW" in element_list:
        print("ERROR in CreateBitsDefinition, N0DW is needed")
        exit(-1)
    if  "N0DW" in element_list and not "N0UP" in element_list:
        print("ERROR in CreateBitsDefinition, N0UP is needed")
        exit(-1)
    if "N1UP" in element_list and not "N1DW" in element_list:
        print("ERROR in CreateBitsDefinition, N1DW is needed")
        exit(-1)
    if  "N1DW" in element_list and not "N1UP" in element_list:
        print("ERROR in CreateBitsDefinition, N1UP is needed")
        exit(-1)

    if signal_type != "":
        bit_def_string = "{:<7}".format(signal_type)
    else:
        bit_def_string = ""
    if "N1UP" in element_list:
        if not (bits_dict["N1UP"] == "0" and bits_dict["N1DW"] == "0"):
            bit_def_string += "{:^9}".format("["+str(bits_dict["N1UP"])+":"+str(bits_dict["N1DW"])+"]")
        else:
            bit_def_string += " "*9
    else:
        bit_def_string += " "*9
    if "N0UP" in element_list:
        if not (bits_dict["N0UP"] == "0" and bits_dict["N0DW"] == "0"):
            bit_def_string += "{:^9}".format("["+str(bits_dict["N0UP"])+":"+str(bits_dict["N0DW"])+"]")
        else:
            bit_def_string += " "*9
    else:
        bit_def_string += " "*9
        
    return bit_def_string


class moddata:
    def __init__(sf, filename = "", module_prefix="", indent="        "):
        sf.filename = filename
        sf.indent=indent
        sf.mod_prefix = module_prefix
        sf.intern_sig_block = ""
        sf.IN_ID = "IN"
        sf.OUT_ID = "OUT"
        sf.INTERN_ID = "INTERN"
        sf.INDIFF_ID = "INDIFF"
        sf.OUTDIFF_ID = "OUTDIFF"
        sf.PARAM_ID = "PARAM"
        sf.modinfo={"module":"",\
                    "import_list" : [],\
                    "parameter_value":[],\
                    "parameter_name":[],\
                    "parameter_bits":[], \
                    "sig_input_name" : [] , \
                    "sig_input_bits":[], \
                    "sig_output_name":[],\
                    "sig_output_bits":[] , \
                    "sig_intern_name": [],\
                    "sig_intern_bits":[],\
                    "sig_input_name_diff":[],\
                    "sig_input_bits_diff":[],\
                    "sig_output_name_diff":[], \
                    "sig_output_bits_diff":[],\
                    "verilog_block":"",\
                    "before_module":""}    

    #########################################################################################################
    # SET FUNCTION
    #########################################################################################################
    def SetModulePrefix(sf, prefix):
        sf.mod_prefix = prefix

    def SetBeforeModule(sf, text):
        sf.modinfo["before_module"] = text

    def SetInternSigBlock(sf, text):
        sf.intern_sig_block = text

    def SetVerilogBlock(sf, verilog_block):
        sf.modinfo["verilog_block"] = verilog_block

    def AppendVerilogLine(sf, verilog_line):
        sf.modinfo["verilog_block"] += verilog_line

    def SetModuleName(sf, module_name):
        sf.modinfo["module"] = module_name


    def SetImportList(sf, import_list):
        sf.modinfo["import_list"] = import_list
        
    def SetInputPortConnections(sf, input_port_connection_list):
        if type(input_port_connection_list) != list :
            print("ERROR in SetInputPortConnections, input_port_connection_list sould be a list")
            exit(-1)
        if len(input_port_connection_list) != len(sf.GetInputSigNamesList()):
            print("ERROR in SetInputPortConnections, input_port_connection_list "
                  "should have the same lenght of sf.GetInputSigNamesList()")
            exit(-1)
        sf.input_port_connection_list = input_port_connection_list
    
    def SetInputDiffPortConnections(sf, input_diff_port_connection_list):
        if type(input_diff_port_connection_list) != list :
            print("ERROR in SetInputDiffPortConnections, input_diff_port_connection_list sould be a list")
            exit(-1)
        if len(input_diff_port_connection_list) != len(sf.GetInputSigDiffNamesList()):
            print("ERROR in SetInputDiffPortConnections, input_diff_port_connection_list "
                  "should have the same lenght of sf.GetInputSigDiffNamesList()")
            exit(-1)
        sf.input_diff_port_connection_list = input_diff_port_connection_list

    def SetOutputPortConnections(sf, output_port_connection_list):
        if type(output_port_connection_list) != list :
            print("ERROR in SetOutputPortConnections, output_port_connection_list sould be a list")
            exit(-1)
        if len(output_port_connection_list) != len(sf.GetOutputSigNamesList()):
            print("ERROR in SetOutputPortConnections, output_port_connection_list "
                    "should have the same lenght of sf.GetOutputSigNamesList()")
            exit(-1)
        sf.output_port_connection_list = output_port_connection_list
    
    def SetOutputDiffPortConnections(sf, output_diff_port_connection_list):
        if type(output_diff_port_connection_list) != list :
            print("ERROR in SetOutputDiffPortConnections, output_diff_port_connection_list sould be a list")
            exit(-1)
        if len(output_diff_port_connection_list) != len(sf.GetOutputSigDiffNamesList()):
            print("ERROR in SetOutputDiffPortConnections, output_diff_port_connection_list "
                  "should have the same lenght of sf.GetOutputSigDiffNamesList()")
            exit(-1)
        sf.output_diff_port_connection_list = output_diff_port_connection_list

    def SetParameterConnections(sf, parameter_connection_list):
        if type(parameter_connection_list) != list :
            print("ERROR in SetParameterConnections, parameter_connection_list sould be a list")
            exit(-1)
        if len(parameter_connection_list) != len(sf.GetParameterNamesList()):
            print("ERROR in SetParameterConnections, paramter_connection_list "
                    "should have the same lenght of sf.GetParameterNamesList()")
            exit(-1)
        sf.parameter_connection_list = parameter_connection_list

    def SetSigAsAnotherModuleSig(sf, other_module, signals_name_list, new_sig_type):
        """ return nothing
        This function copy a signal property of another module in current module, for 
        example suppose that other_module (a moddata class object) have an input signal
        called "signal1" with 4 bit, if we call SetSigAsOtherModuleSig(other_module, "signal1", other_module.OUT_ID) 
        the current module will copy "signal1" property in the output signal list.
        The change of type can be done only for non parameter signals, parameter signal will remain the same
        """
    
        for signal_name in signals_name_list:
            sig_data = other_module.GetSigData(signal_name)
            if sig_data[0] == True:
                sig_data = sig_data[1]
                old_sig_type = sig_data[0]
                if old_sig_type != sf.PARAM_ID:
                    sig_name = sig_data[1]
                    sig_bits = sig_data[2]
                    if new_sig_type == sf.IN_ID:
                        sf.modinfo["sig_input_name"].append(sig_name)
                        sf.modinfo["sig_input_bits"].append(sig_bits)
                    elif new_sig_type == sf.OUT_ID:
                        sf.modinfo["sig_output_name"].append(sig_name)
                        sf.modinfo["sig_output_bits"].append(sig_bits)
                    elif new_sig_type == sf.INTERN_ID:
                        sf.modinfo["sig_intern_name"].append(sig_name)
                        sf.modinfo["sig_intern_bits"].append(sig_bits)
                    elif new_sig_type == sf.INDIFF_ID:
                        sf.modinfo["sig_input_name_diff"].append(sig_name)
                        sf.modinfo["sig_input_bits_diff"].append(sig_bits)
                    elif new_sig_type == sf.OUTDIFF_ID:
                        sf.modinfo["sig_output_name_diff"].append(sig_name)
                        sf.modinfo["sig_output_bits_diff"].append(sig_bits)
                    else:
                        return 1
                else:
                    sf.modinfo["parameter_name"].append(sig_data[1])
                    sf.modinfo["parameter_bits"].append(sig_data[2])
                    sf.modinfo["parameter_value"].append(sig_data[3])

            else:
                # Return 1 if the signal there ins't in the other_module
                return 1  
        
        sf.input_port_connection_list = sf.modinfo["sig_input_name"]
        sf.input_diff_port_connection_list = sf.modinfo["sig_input_name_diff"]
        sf.output_port_connection_list = sf.modinfo["sig_output_name"]
        sf.output_diff_port_connection_list = sf.modinfo["sig_output_name_diff"]
        sf.parameter_connection_list = sf.modinfo["parameter_name"]

        return 0

    def SetInternSigFromOtherModuleSearchingInVerilogCode(sf, other_module):
        """
        This function search in sf.GetVerilogBlock() each signals of other_module and 
        init is as internal if exist.
        """
        if sf.modinfo["verilog_block"] == "":
            print("ERROR in SetInternalSigFromOtherModuleSearchingInVerilogCode, verilog code block empty")
            exit(-1)

        for sig_name, sig_bits in zip(other_module.GetInputSigNamesList(),other_module.GetInputSigBitsList()):
            match_res = re.match(r".*\W"+sig_name+"\W.*", sf.modinfo["verilog_block"].replace("\n",""))
            if match_res is not None and not sig_name in sf.GetAllIoSigName():
                sf.modinfo["sig_intern_name"].append(sig_name)
                sf.modinfo["sig_intern_bits"].append(sig_bits)

        for sig_name, sig_bits in zip(other_module.GetOutputSigNamesList(),other_module.GetOutputSigBitsList()):
            match_res = re.match(r".*\W"+sig_name+"\W.*", sf.modinfo["verilog_block"].replace("\n",""))
            if match_res is not None and not sig_name in sf.GetAllIoSigName():
                sf.modinfo["sig_intern_name"].append(sig_name)
                sf.modinfo["sig_intern_bits"].append(sig_bits)

        for sig_name, sig_bits in zip(other_module.GetInternSigNamesList(),other_module.GetInternSigBitsList()):
            match_res = re.match(r".*\W"+sig_name+"\W.*", sf.modinfo["verilog_block"].replace("\n",""))
            if match_res is not None and not sig_name in sf.GetAllIoSigName():
                sf.modinfo["sig_intern_name"].append(sig_name)
                sf.modinfo["sig_intern_bits"].append(sig_bits)

    #########################################################################################################
    # Deletion FUNCTION
    #########################################################################################################

    def DeleteVerilogBlock(sf):
        sf.modinfo["verilog_block"] = ""

    def DeleteInternSigs(sf):
        sf.modinfo["sig_intern_name"] = []
        sf.modinfo["sig_intern_bits"] = []

    #########################################################################################################
    # Elaboration FUNCTION
    #########################################################################################################


    def Analyze(sf, moddata_similar=0, hravulog=False):
        """ Return none
        This function analyze the verilog file (set in object init) and it saves info
        about the module.
        modinfo_similar -> This optional argument should contain a moddata object.
            When this object is given, each input and output are seached in modinfo_similar object
            and are saved as "different", so when you then call for example OutputSigNamesList()
            this function  will return a list with all output signal both in the filename and in the
            modinfo_similar object. The remaining signals can be seen using OutputSigDiffNamesList().
        """
        if sf.filename == "":
            return 1
        fp = open(sf.filename, "r")

        sig_input_name = [] 
        sig_input_bits = [] 
        sig_input_name_diff = [] 
        sig_input_bits_diff = [] 
        sig_output_name = [] 
        sig_output_bits = [] 
        sig_output_name_diff = [] 
        sig_output_bits_diff = [] 
        mod_patt="^module "
        parameter_name = [] 
        parameter_bits = [] 
        parameter_value = [] 
        sig_intern_name = [] 
        sig_intern_bits = [] 
        import_list = []

        sf.sections_lines = {"before_module":[0,0], "io":[0,0], "intern":[0,0], "verilog_block":[0,0] }

        cnt=0
        lineno=0
        save_intern_signals=0
        save_before_module=True
        end_iodecl=False

        for line in fp.readlines():
            comment_line = line
            line = RemoveComments(line)
            line = line.replace("\t"," ")
            if "import " in line:
                import_list.append(line)
            if ");" in line and not end_iodecl:
                sf.sections_lines["io"][1] = lineno
                sf.sections_lines["intern"][0] = lineno+1

            if not save_intern_signals:
                if (" input " in line) or (" output " in line):
                    real_line = " ".join(line.split()).replace(',','')

                if " input " in line:
                    if moddata_similar!=0 and not real_line.split()[-1] in moddata_similar.GetInputSigNamesList():
                        sig_input_name_diff.append(real_line.split()[-1])
                        sig_input_bits_diff.append(GetBits(line))
                    else:
                        sig_input_name.append(real_line.split()[-1])
                        sig_input_bits.append(GetBits(line))
        
                if " output " in line:
                    if moddata_similar!=0 and not real_line.split()[-1] in moddata_similar.GetOutputSigNamesList():
                        sig_output_name_diff.append(real_line.split()[-1])
                        sig_output_bits_diff.append(GetBits(line))
                    else:
                        sig_output_name.append(real_line.split()[-1])
                        sig_output_bits.append(GetBits(line))
                if re.match(mod_patt,line):
                    module = line.split(" ")[1].strip()
                    save_before_module=False
                    sf.sections_lines["before_module"] = [0,lineno]
                    sf.sections_lines["io"]  = [lineno+1,0]

                if re.match("^\W*parameter.*", line):
                    real_line=" ".join(line.split()).strip()
                    real_line=real_line.replace(",","").strip()
                    l1=real_line.split("=")
                    l=l1[0].strip().split(" ")
                    parameter_name.append(l[-1])
                    if "[" in l[-1] :
                        print("not implemented!!")
                        exit(-1)
                    else:
                        parameter_bits.append(1)
                    parameter_value.append(l1[1].strip())
            else:
                line_split = " ".join(line.strip().replace(";","").replace("\t","").replace(","," ").split())
                line_split = line_split.split(" ")
                if len(line_split)!=0 and line_split[0] == "logic":
                    for word in line_split[1:]:
                        if not "[" in word:
                            sig_intern_name.append(word)
                            sig_intern_bits.append(GetBits(line))
                    decl_line=lineno
                
                if "END_DECLARATIONS" in comment_line:
                    decl_line = lineno
                

            if save_before_module:
                sf.modinfo["before_module"] += line

            if cnt==0 and "#(" in line:
                cnt+=1
            elif ( cnt==2 or cnt==0 ) and "(" in line:
                cnt+=1
            # end for
            elif ( cnt==3 or cnt == 1 ) and ");" in line:
                end_iodecl = True
                decl_line = lineno
                save_intern_signals=1
                cnt+=1
            elif cnt==1 and ")" in line:
                cnt+=1

            lineno+=1

        sf.sections_lines["intern"][1] = decl_line
        sf.sections_lines["verilog_block"] = [decl_line+1,lineno-1]

        sf.modinfo={"module":module,\
                    "import_list":import_list,\
                    "parameter_value":parameter_value,\
                    "parameter_name":parameter_name,\
                    "parameter_bits":parameter_bits, \
                    "sig_input_name" : sig_input_name , \
                    "sig_input_bits":sig_input_bits, \
                    "sig_output_name":sig_output_name,\
                    "sig_output_bits":sig_output_bits , \
                    "sig_intern_name": sig_intern_name,\
                    "sig_intern_bits":sig_intern_bits,\
                    "sig_input_name_diff":sig_input_name_diff,\
                    "sig_input_bits_diff":sig_input_bits_diff,\
                    "sig_output_name_diff":sig_output_name_diff, \
                    "sig_output_bits_diff":sig_output_bits_diff,\
                    "verilog_block":""}    
        sf.input_port_connection_list = sig_input_name
        sf.input_diff_port_connection_list = sig_input_name_diff
        sf.output_port_connection_list = sig_output_name
        sf.output_diff_port_connection_list = sig_output_name_diff
        sf.parameter_connection_list = parameter_name

        return 0
        

    #########################################################################################################
    # GET FUNCTION
    #########################################################################################################

    def GetAllIds(sf):
        return  [sf.IN_ID, sf.OUT_ID, sf.INTERN_ID, sf.INDIFF_ID, sf.OUTDIFF_ID, sf.PARAM_ID]

    def GetBeforeModuleLines(sf):
        return sf.sections_lines["before_module"]

    def GetIoLines(sf):
        return sf.sections_lines["io"]

    def GetInternLines(sf):
        return sf.sections_lines["intern"]

    def GetVerilogBlockLines(sf):
        return sf.sections_lines["verilog_block"]

    
    def GetModuleName(sf):
        return sf.modinfo["module"]

    def GetParameterNamesList(sf):
        return sf.modinfo["parameter_name"]

    def GetParameterBitsList(sf):
        return sf.modinfo["parameter_bits"]

    def GetParameterValuesList(sf):
        return sf.modinfo["parameter_value"]

    def GetInputSigNamesList(sf):
        return sf.modinfo["sig_input_name"]

    def GetInputSigBitsList(sf):
        return sf.modinfo["sig_input_bits"]

    def GetInputSigDiffNamesList(sf):
        return sf.modinfo["sig_input_name_diff"]

    def GetInputSigDiffBitsList(sf):
        return sf.modinfo["sig_input_bits_diff"]

    def GetOutputSigNamesList(sf):
        return sf.modinfo["sig_output_name"]

    def GetOutputSigBitsList(sf):
        return sf.modinfo["sig_output_bits"]

    def GetOutputSigDiffNamesList(sf):
        return sf.modinfo["sig_output_name_diff"]

    def GetOutputSigDiffBitsList(sf):
        return sf.modinfo["sig_output_bits_diff"]
    
    def GetInternSigNamesList(sf):
        return sf.modinfo["sig_intern_name"]
    
    def GetInternSigBitsList(sf):
        return sf.modinfo["sig_intern_bits"]

    def GetAllIoSigName(sf):
        return sf.GetInputSigNamesList() + sf.GetOutputSigNamesList()  

    def GetAllIoSigBits(sf):
        return sf.GetInputSigBitsList() + sf.GetOutputSigBitsList() 
    def GetAllIoSigType(sf):
        ret = []
        for sig in sf.GetInputSigNamesList():
            ret.append(sf.IN_ID)

        for sig in sf.GetOutputSigNamesList():
            ret.append(sf.OUT_ID)
        
        return ret
    def GetAllDiffSigName(sf):
        return sf.GetInputSigDiffNamesList() + sf.GetOutputSigDiffNamesList()

    def GetAllDiffSigType(sf):
        ret = []
        for sig in sf.GetInputSigDiffNamesList():
            ret.append(sf.INDIFF_ID)

        for sig in sf.GetOutputSigDiffNamesList():
            ret.append(sf.OUTDIFF_ID)
        
        return ret


    def GetAllSigName(sf):
        return sf.GetInputSigNamesList() + sf.GetOutputSigNamesList() + sf.GetInternSigNamesList() 
    
    def GetAllSigBits(sf):
        return sf.GetInputSigBitsList() + sf.GetOutputSigBitsList() + sf.GetInternSigBitsList()


    def GetAllConnectionSigNameAndBits(sf):
        conn_list = sf.input_port_connection_list
        conn_list += sf.output_port_connection_list
        conn_list += sf.input_diff_port_connection_list
        conn_list += sf.output_diff_port_connection_list
        bit_list = sf.GetInputSigBitsList()
        bit_list += sf.GetOutputSigBitsList()
        bit_list += sf.GetInputSigDiffBitsList()
        bit_list += sf.GetOutputSigDiffBitsList()
       
        return [conn_list, bit_list]

    def GetSigData(sf, signal_name):
        """ Return data related to a signal, only bits and dame at the moment
        """
        [exist, sig_type, i ] = sf.SigExist(signal_name)
        if exist == False:
            return [False,[]]
    
        if sig_type == sf.IN_ID:
            return [True,[sf.IN_ID, sf.GetInputSigNamesList()[i],sf.GetInputSigBitsList()[i]]]

        if sig_type == sf.OUT_ID:
            return [True,[sf.OUT_ID, sf.GetOutputSigNamesList()[i],sf.GetOutputSigBitsList()[i]]]

        if sig_type == sf.PARAM_ID:
            return [True,[sf.PARAM_ID,sf.GetParameterNamesList()[i],sf.GetParameterBitsList()[i],sf.GetParameterValuesList()[i]]]

        if sig_type == sf.INTERN_ID:
            return [True,[sf.INTERN_ID, sf.GetInternSigNamesList()[i],sf.GetInternSigBitsList()[i]]]

        if sig_type == sf.INDIFF_ID:
            return [True,[sf.INDIFF_ID, sf.GetInputSigDiffNamesList()[i], sf.GetInputSigDiffBitsList()[i]]]

        if sig_type == sf.OUTDIFF_ID:
            return [True,[sf.OUTDIFF_ID, sf.GetOutputSigDiffNamesList()[i], sf.GetOutputSigDiffBitsList()[i]]]

        print("ERROR in GetSigData, internal error")
        exit(-1)

    def GetVerilogBlock(sf):
        return sf.modinfo["verilog_block"]

    def GetIndent(sf, indent_level=1):
        return sf.indent*indent_level

    def GetModuleNameNoPrefix(sf):
        return sf.GetModuleName().replace(sf.mod_prefix,"")

    def GetIndent(sf, indent_level=1):
        return sf.indent*indent_level

    def GetModuleNameNoPrefix(sf):
        return sf.GetModuleName().replace(sf.mod_prefix,"")
    
    def GetParamBase(sf):
        return GetParamBase(sf.GetModuleName())
    
    def GetParamBaseNoPrefix(sf):
        return GetParamBase(sf.GetModuleNameNoPrefix())

    def GetImportList(sf):
        return sf.modinfo["import_list"]


    def AppendInternSig(sf, name, bits):
        sf.modinfo["sig_intern_name"].append(name)
        sf.VerifyBitsDict(bits)
        sf.modinfo["sig_intern_bits"].append(bits)

    def VerifyBitsDict(sf, bits_dict):
        if type(bits_dict) != dict:
            print("Error in AppendIntern, bits_dict should be a list")
        element_list = []
        for key in bits_dict.keys():
            # only N0 and N1 supported at the moment
            if key != "N0UP" and key!="N0DW" and key!="N1UP" and key!="N1DW":
                print("ERROR in  CreateBitsDefinition, key in bits_dict not suppoted (%s)" % key)
                exit(-1)
            element_list.append(key)

        # Now the order will be ['N0DW', 'N0UP', 'N1DW', 'N1UP']
        if "N0UP" in element_list and not "N0DW" in element_list:
            print("ERROR in CreateBitsDefinition, N0DW is needed")
            exit(-1)
        if  "N0DW" in element_list and not "N0UP" in element_list:
            print("ERROR in CreateBitsDefinition, N0UP is needed")
            exit(-1)
        if "N1UP" in element_list and not "N1DW" in element_list:
            print("ERROR in CreateBitsDefinition, N1DW is needed")
            exit(-1)
        if  "N1DW" in element_list and not "N1UP" in element_list:
            print("ERROR in CreateBitsDefinition, N1UP is needed")
            exit(-1)

    
    def GetPortIoFromList(sf, sig_name_list, ending=False, change_bit=False, indent_level=1):
        """ Return a string with port definition
        sig_name_list  -> it is a list of signal belonging to this object
            , the signal in this list will be init as verilog port declaration
        ending -> il false a ",\n" is placed at the end of each line, il True
            the last declaration have only "\n" string at the end
        change_bit -> this option is used to change the number of bit of the
            signals, the order of the bits are
             input logic [N1UP:N1DW] [N0UP:N0DW] sig  [N3UP:N3DW] [N2UP:N2DW]
            so change_bit should be a dictionary like this:
                {"N1UP":2 , "N1DW":0}
            If the signal was "input logic [31:0] sig1" it became:
                input logic [2:0] [31:0] sig1
        indent_level -> is a number that indicate the indentation level to use
        """
        
        #### Controls
        if type(sig_name_list)!=list:
            print("ERROR in GetPortIo, sig_name_list should be a list of signals")
            exit(-1)
        if change_bit != False and type(change_bit)!= dict:
            element_list.append(key)

        # Now the order will be ['N0DW', 'N0UP', 'N1DW', 'N1UP']
        if "N0UP" in element_list and not "N0DW" in element_list:
            print("ERROR in VerifyBitsDict, N0DW is needed")
            exit(-1)
        if  "N0DW" in element_list and not "N0UP" in element_list:
            print("ERROR in VerifyBitsDict, N0UP is needed")
            exit(-1)
        if "N1UP" in element_list and not "N1DW" in element_list:
            print("ERROR in VerifyBitsDict, N1DW is needed")
            exit(-1)
        if  "N1DW" in element_list and not "N1UP" in element_list:
            print("ERROR in VerifyBitsDict, N1UP is needed")
            exit(-1)


    
    def GetPortIoFromList(sf, sig_name_list, ending=False, change_bit=False, indent_level=1, override = False):
        """ Return a string with port definition
        sig_name_list  -> it is a list of signal belonging to this object
            , the signal in this list will be init as verilog port declaration
        ending -> il false a ",\n" is placed at the end of each line, il True
            the last declaration have only "\n" string at the end
        change_bit -> this option is used to change the number of bit of the
            signals, the order of the bits are
             input logic [N1UP:N1DW] [N0UP:N0DW] sig  [N3UP:N3DW] [N2UP:N2DW]
            so change_bit should be a dictionary like this:
                {"N1UP":2 , "N1DW":0}
            If the signal was "input logic [31:0] sig1" it became:
                input logic [2:0] [31:0] sig1
        indent_level -> is a number that indicate the indentation level to use
        """
        
        #### Controls
        if type(sig_name_list)!=list:
            print("ERROR in GetPortIo, sig_name_list should be a list of signals")
            exit(-1)
        if change_bit != False and type(change_bit)!= dict:
            print("ERROR in GetPortIo, change_bit should be a dictionary")
            exit(-1)
        
        #### Elaboration
        io_definition_from_list = ""

        sig_type = ""
        for sig in sig_name_list:
            line_to_create = ""
            line_to_create += sf.GetIndent(indent_level)

            # If INPUT signal
            if sig in sf.GetInputSigNamesList():
                line_to_create += "input  "
                bit_list_index = sf.GetInputSigNamesList().index(sig)
                bit_dict = sf.GetInputSigBitsList()[bit_list_index]
                if change_bit != False:
                    for bit_key in change_bit.keys():
                        if not ( not override and bit_key in bit_dict.keys() ):
                            bit_dict[bit_key] = change_bit[bit_key]

                
                # At the moment only logic input are supported
                line_to_create += CreateBitsDefinition(bit_dict, "logic")
                sig_type = "IO"
            
            # If OUTPUT signal
            elif sig in sf.GetOutputSigNamesList():
                line_to_create += "output "
                bit_list_index = sf.GetOutputSigNamesList().index(sig)
                bit_dict = sf.GetOutputSigBitsList()[bit_list_index]
                if change_bit != False:
                    for bit_key in change_bit.keys():
                        if not ( not override and bit_key in bit_dict.keys() ):
                            bit_dict[bit_key] = change_bit[bit_key]
                
                # At the moment only logic input are supported
                line_to_create += CreateBitsDefinition(bit_dict, "logic")
                sig_type = "IO"

            # if INTERNAL signal
            elif sig in sf.GetInternSigNamesList():
                bit_list_index = sf.GetInternSigNamesList().index(sig)
                bit_dict = sf.GetInternSigBitsList()[bit_list_index]
                if change_bit != False:
                    for bit_key in change_bit.keys():
                        if not ( not override and bit_key in bit_dict.keys() ):
                            bit_dict[bit_key] = change_bit[bit_key]
                # At the moment only logic input are supported
                line_to_create += CreateBitsDefinition(bit_dict, "logic")
                sig_type = "INTERN"

            else:
                print("ERROR signal %s not found in %d module" %(sig, sf.GetModuleName()))
                exit(-1)

            line_to_create += sig + " "
            
            if ending == False or ( ending==True and sig != sig_name_list[-1]):
                if sig_type == "INTERN":
                    line_to_create += ";"
                else:
                    line_to_create += ","

            line_to_create +="\n"

            io_definition_from_list += line_to_create
    
        
        return io_definition_from_list

    def GetParameterDeclaration(sf,indent_level=0):
        """ Return the declaration of the parameter of the block
        """
        declaration_str = ""
        indent_1 = sf.GetIndent(indent_level)
        indent_2 = indent_1 + sf.GetIndent(1)

        parameter_name_list = sf.GetParameterNamesList()
        if parameter_name_list != []:
            end_str = ",\n"
            for par_name, par_value in zip(parameter_name_list, sf.GetParameterValuesList()):
                if par_name == parameter_name_list[-1]:
                    end_str = "\n"
                declaration_str += indent_2 + "parameter "+ "{:<20}".format(par_name) + "= "+par_value + end_str

        if declaration_str != "":
            return indent_1 + "#(\n" + declaration_str + indent_1 + ")\n"
        return declaration_str

    def GetDeclaration(sf, indent_level=0, change_bit_all_io = False, no_change_bit_name_list = []):
        """ Return the declaration of the block
        """
        declaration_str = ""
        indent_1 = sf.GetIndent(indent_level)
        indent_2 = indent_1 + sf.GetIndent(1)

        
        #### PARAMETERS
        if sf.GetParameterNamesList() != []:
            declaration_str += sf.GetParameterDeclaration(indent_level)
        
        #### INPUTS AND OUTPUTS
        declaration_str += "(\n"
        input_list = []
        if no_change_bit_name_list != []:
            for sig in sf.GetInputSigNamesList():
                if not sig in no_change_bit_name_list:
                    input_list.append(sig)
                else:
                    declaration_str += sf.GetPortIoFromList([sig])
        else:
            input_list = sf.GetInputSigNamesList()
        declaration_str += sf.GetPortIoFromList(input_list, change_bit = change_bit_all_io)
        
        output_list = []
        if no_change_bit_name_list != []:
            for sig in sf.GetOutputSigNamesList():
                if not sig in no_change_bit_name_list:
                    output_list.append(sig)
                else:
                    declaration_str += sf.GetPortIoFromList([sig])
        else:
            output_list = sf.GetOutputSigNamesList()
        declaration_str += sf.GetPortIoFromList(output_list, ending=True, change_bit = change_bit_all_io)
        declaration_str += ");\n"

        #### INTERNAL signals
        if sf.intern_sig_block != "":
            declaration_str += sf.intern_sig_block
        else:
            declaration_str += sf.GetPortIoFromList(sf.GetInternSigNamesList())

        return declaration_str

    def GetCompleteVerilog(sf):
        datafile = ""
        if sf.VerilogBlockExist():
            if "before_module" in sf.modinfo.keys():
                datafile += sf.modinfo["before_module"]
            #### IMPORTS
            if sf.GetImportList() != []:
                for impo in sf.GetImportList():
                    if not impo.strip() in datafile.split("\n"):
                        datafile += impo + "\n"
            datafile += "\n\n"
            datafile += "module " + sf.GetModuleName() + "\n"
            datafile += sf.GetDeclaration()
            datafile += "\n\n"
            datafile += sf.GetVerilogBlock()
            datafile += "endmodule\n"
            return datafile
        return ""


    def GetInstance(sf, inst_name, indent_level=1):
        """ Return a string containing the verilog instance of the module
        inst_name -> It is the name of the instance
        connection_input_list -> list of signals to connect input
        connection_output_list -> list od signals to connect output
        connection_param_list -> list of parameter to connect to module parameter
        indent_level -> level of indentation of the first line of the instance
        """
        
        #### Elaboration    
        instance_str = ""
        indent_1 = sf.GetIndent(indent_level)
        indent_2 = indent_1 + sf.GetIndent(1)
        
        instance_str += indent_1 + sf.GetModuleName()

        parameter_name_list = sf.GetParameterNamesList()

        if len(parameter_name_list) >= 1:
            instance_str +="\n"+ indent_1 + "#( \n"
            for par, par_to_conn in zip(parameter_name_list,sf.parameter_connection_list) :
                if par==parameter_name_list[-1]:
                    instance_str += indent_2 +" .{:<20}".format(par) +"( "+" {:<20}".format(par_to_conn)+") \n"
                else:
                    instance_str += indent_2 + " .{:<20}".format(par) +"( "+ " {:<20}".format(par_to_conn) +"),\n"
            instance_str += indent_1 +")\n" + indent_1 
        
        instance_str += " " +inst_name + "\n"
        instance_str += indent_1 + "(\n"
            
        # INPUTS
        instance_str += indent_2 + "// Input ports of "+inst_name+"\n"
        for port_input_sig, to_connect_input_sig in zip(sf.GetInputSigNamesList(),sf.input_port_connection_list):
            instance_str += indent_2+"."+"{:<23}".format(port_input_sig)\
                                  +"( "+" {:<32}".format(to_connect_input_sig)+" ),\n"


        # DIFF INPUT
        if sf.input_diff_port_connection_list != []:
            instance_str += "\n"+ indent_2 + "// Input diff ports of "+inst_name+"\n"
            for port_input_sig, to_connect_input_sig in \
                zip(sf.GetInputSigDiffNamesList(),sf.input_diff_port_connection_list):
                instance_str += indent_2+"."+"{:<23}".format(port_input_sig)\
                                      +"( "+" {:<32}".format(to_connect_input_sig)+" ),\n"

        # OUTPUT
        instance_str += "\n"+ indent_2 + "// Output ports of "+inst_name+"\n"
        end_str=" ),\n"
        for port_output_sig, to_connect_output_sig in zip(sf.GetOutputSigNamesList(),sf.output_port_connection_list):
            if sf.output_diff_port_connection_list == [] and port_output_sig == sf.GetOutputSigNamesList()[-1]:
                end_str = " )\n"
            instance_str += indent_2+"."+"{:<23}".format(port_output_sig)\
                                  +"( "+" {:<32}".format(to_connect_output_sig) + end_str

        # DIFF OUTPUT
        if sf.output_diff_port_connection_list != []:
            instance_str += "\n"+ indent_2 + "// Output diff ports of "+inst_name+"\n"
            end_str=" ),\n"
            for port_output_sig, to_connect_output_sig in \
                zip(sf.GetOutputSigDiffNamesList(),sf.output_diff_port_connection_list):
                if port_output_sig == sf.GetOutputSigDiffNamesList()[-1]:
                    end_str = " )\n"
                instance_str += indent_2+"."+"{:<23}".format(port_output_sig)\
                                      +"( "+" {:<32}".format(to_connect_output_sig) + end_str

        instance_str += indent_1 + ");\n"

        return instance_str

    
    ##################################################################################################
    # FIND and VERIFY functions
    ##################################################################################################
    
    def SigExist(sf, signal_name):
        """ Return this list: [ 1 IfExist, sig type (IN,OUT,PARAM,INTERN,INDIFF, OUTDIFF), index in the list ]
        """
        if signal_name in sf.GetInputSigNamesList():
            sig_type=sf.IN_ID
            index = sf.GetInputSigNamesList().index(signal_name)
            return [True, sig_type, index]
        
        if signal_name in sf.GetOutputSigNamesList():
            sig_type=sf.OUT_ID
            index = sf.GetOutputSigNamesList().index(signal_name)
            return [True, sig_type, index]
        
        if signal_name in sf.GetParameterNamesList():
            sig_type=sf.PARAM_ID
            index = sf.GetParameterNamesList().index(signal_name)
            return [True, sig_type, index]
        
        if signal_name in sf.GetInternSigNamesList():
            sig_type=sf.INTERN_ID
            index = sf.GetInternSigNamesList().index(signal_name)
            return [True, sig_type, index]

        if signal_name in sf.GetInputSigDiffNamesList():
            sig_type=sf.INDIFF_ID
            index = sf.GetInputSigDiffNamesList().index(signal_name)
            return [True, sig_type, index]

        if signal_name in sf.GetOutputSigDiffNamesList():
            sig_type=sf.OUTDIFF_ID
            index = sf.GetOutputSigDiffNamesList().index(signal_name)
            return [True, sig_type, index]

        return [False,"None",0]

    def VerilogBlockExist(sf):
        return (sf.modinfo["verilog_block"]!="")


    




#DIR="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/"
#filename=DIR+"cv32e40p/rtl/cv32e40p_if_stage_no_ft.sv"
#testAnalyze(filename)
#testGetPortIo(filename)
#testGetInstance(filename)
#testGetDeclaration(filename)
#testGetSigData(filename)
#testSetSigAsAnotherModuleSig(filename)
