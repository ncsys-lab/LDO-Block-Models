import json
import yaml
import matplotlib.pyplot as plt
import numpy as np

def read_yaml( f ):
    with open(f, 'r') as stream:
        return yaml.safe_load(stream)

def compute_tau(VREF, VREG, kwargs):
    print(kwargs)
    return VREF * kwargs['VREF_to_tau'] + VREG * kwargs['VREG_to_tau'] + kwargs['const_tau']

def compute_response_time(VREF, VREG, kwargs):
    return VREF * kwargs['VREF_to_response_time'] + VREG * kwargs['VREG_to_response_time'] + kwargs['const_response_time']

params = read_yaml("./regression_results.yaml")


f = open("./jsondatadump.json")

fixture_sims = json.load(f)

f.close()

paramdict_tau = dict(map(lambda p:(p[0],p[1]['const_1']), params['tau'].items()))
print(paramdict_tau)

paramdict_response_time = dict(map(lambda p:(p[0],p[1]['const_1']), params['response_time'].items()))
print(paramdict_response_time)

def response(t, tau, response_time):
    if(t < response_time):
        return 0.0
    else:
        print(t)
        result = 3.3 * ( 1 - (np.e)**(-(t - response_time)/tau) )
        print(result)
        return result

error = 0

for sim in fixture_sims.keys():
    time = fixture_sims[sim]['rp'][0]
    vreg = fixture_sims[sim]['inp'][1][0]
    vref = fixture_sims[sim]['inn'][1][0]

    tau = compute_tau(vref, vreg, paramdict_tau)
    response_time = compute_response_time(vref, vreg, paramdict_response_time)
    print(vref)
    print(vreg)
    print(tau)

    vec_response = np.vectorize(response)
    response_vec = vec_response(time, tau, response_time )
    print(response_vec)
    print(time)
    
    ploterror = np.sum((fixture_sims[sim]['rp'][1] - response_vec)**2,0)
    error = error + ploterror
    
    print("error in plot: {}".format(ploterror))

    if(False):
        plt.plot(fixture_sims[sim]['rp'][0],fixture_sims[sim]['rp'][1], label='experimental')
        plt.plot(time, response_vec, label='model')
        plt.legend(loc='best')
        plt.show()

print("Average Error: {}".format(error / len(fixture_sims.keys())))

