import json
import yaml
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp


def read_yaml( f ):
    with open(f, 'r') as stream:
        return yaml.safe_load(stream)

class ComparatorLatchModel:

    states = {
        'precharge' :             0,
        'evaluate_high' :         1,
        'evaluate_low_high_low' : 2,
        'evaluate_low_stable' :   3,
        'evaluate_low_low_high' : 4,
        'evaluate_wait_low_high': 5,
        'evaluate_wait_high_low': 6
    }

    def __init__(self, VREF, VREG, low_high_param_yaml_path = "./regression_results_zero_one.yaml", high_low_param_yaml_path = "./regression_results_one_zero.yaml"):

        low_high_param = read_yaml(low_high_param_yaml_path)
        high_low_param = read_yaml(high_low_param_yaml_path)

        self.high_low_paramdict_tau      = dict(map(lambda p:(p[0],p[1]['const_1']), high_low_param['tau'].items()))          
        self.high_low_paramdict_resptime = dict(map(lambda p:(p[0],p[1]['const_1']), high_low_param['response_time'].items()))

        self.low_high_paramdict_tau      = dict(map(lambda p:(p[0],p[1]['const_1']), low_high_param['tau'].items()))
        self.low_high_paramdict_resptime = dict(map(lambda p:(p[0],p[1]['const_1']), low_high_param['response_time'].items()))
        self.state = ComparatorLatchModel.states['precharge']
        self.clk = 0
        self.prev_clk = 0
        self.VREF = VREF
        self.VREG = VREG
        self.delay_time = 0

    def poke(self, pin, value):
        return setattr(self, pin, value)
    
    def model_ddt(self, y, t):
        
        if(self.state == ComparatorLatchModel.states['precharge']): #precharge state
            #print('======================= {} ======================='.format(self.state))
            if(self.clk == 3.3 and self.prev_clk == 0):
                if(self.VREG > self.VREF):
                    self.state = ComparatorLatchModel.states['evaluate_wait_high_low']
                    #print(t)
                    self.delay_time = t
                else:
                    self.state = ComparatorLatchModel.states['evaluate_high']
            self.prev_clk = self.clk
            return [0]
        
        elif(self.state == ComparatorLatchModel.states['evaluate_high']): #evaluation high
            #print('======================= {} ======================='.format(self.state))
            if(self.clk == 0 and self.prev_clk == 3.3):
                self.state = ComparatorLatchModel.states['precharge']
            else:
                self.state = ComparatorLatchModel.states['evaluate_high']
            self.prev_clk = self.clk
            return [0]
        
        elif(self.state == ComparatorLatchModel.states['evaluate_wait_high_low']):
            #print('======================= {} ======================='.format(self.state))
            #print(t)
            #print(self.delay_time)
            
            response_time = compute_response_time(self.VREF, self.VREG, self.high_low_paramdict_resptime)
            #print(response_time)
            if( t - self.delay_time  > response_time ):
                self.state = ComparatorLatchModel.states['evaluate_low_high_low']
            self.prev_clk = self.clk
            return [0]

        elif(self.state == ComparatorLatchModel.states['evaluate_low_high_low']):
            #print('======================= {} ======================='.format(self.state))
            tau = compute_tau(self.VREF, self.VREG, self.high_low_paramdict_tau)
            #print(tau)
            if(self.prev_clk == 3.3 and self.clk == 0):
                self.state = ComparatorLatchModel.states['evaluate_wait_low_high']
                self.delay_time = t
            self.prev_clk = self.clk
            
            return [-y[0] / tau]
        
        elif(self.state == ComparatorLatchModel.states['evaluate_wait_low_high']):
            #print('======================= {} ======================='.format(self.state))
            response_time = compute_response_time(self.VREF, self.VREG, self.low_high_paramdict_resptime)
            if(t -self.delay_time > response_time):
                self.state = ComparatorLatchModel.states['evaluate_low_low_high']
            self.prev_clk = self.clk
            return [0]  

        elif(self.state == ComparatorLatchModel.states['evaluate_low_low_high']):
            #print('======================= {} ======================='.format(self.state))
            
            tau = compute_response_time(self.VREF, self.VREG, self.low_high_paramdict_resptime)
            if( 3.3 - y[0] < 0.0001 ):
                self.state = ComparatorLatchModel.states['precharge']
            self.prev_clk = self.clk
            return [((3.3 - y[0]) / tau)]      


    
def compute_tau(VREF, VREG, kwargs):
    return VREF * kwargs['VREF_to_tau'] + VREG * kwargs['VREG_to_tau'] + kwargs['const_tau']

def compute_response_time(VREF, VREG, kwargs):
    return VREF * kwargs['VREF_to_response_time'] + VREG * kwargs['VREG_to_response_time'] + kwargs['const_response_time']

tmax = 1e-8
VREG = 1.6
VREF = 3.3
sample_points = 1000

model = ComparatorLatchModel(VREF, VREG)

tiv = (0,tmax)
times = np.linspace(0, tmax, sample_points)
o = np.zeros(sample_points)
y = [3.3]

clk0 = np.full(250, 0)
clk1 = np.full(500, 3.3)
clk2 = np.full(250, 0)

clk = np.concatenate((clk0,clk1,clk2))

for t in enumerate(times):
    model.poke('clk', clk[t[0]])
    
    o[t[0]] = y[0]
    y[0] = y[0] + model.model_ddt(y, t[1])[0] * ( tmax / sample_points )


plt.plot(times, o,   label='out')
plt.plot(times, clk, label='clk')
plt.legend(loc='best')
plt.xlabel('t')
plt.grid()
plt.show()