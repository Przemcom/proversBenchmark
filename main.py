import os
import toml as toml
# import nltk
import subprocess

# current working directory
cwd = os.path.abspath(os.path.dirname(__file__))

default_config_fname = os.path.join(cwd, 'default_config.toml')
config_fname = os.path.join(cwd, 'config.toml')


def my_setup():
    """
    Loads default config file with fields description and asks user for
    parameters.
    """
    new_params = {}
    params = load_params(fname=config_fname)
    sep = 8 * " " + 8 * "*" + 8 * " "

    print(sep + "You will now have to set parameters for benchmark.\n" +
          sep + "    Default values are printed between brackets.\n" +
          sep + "    Leave blank if you want to use default value")

    for param in params:
        new_params[param] = {}
        values = params[param]['value']
        descriptions = params[param]['description']
        for value in values:
            new_params[param][value] = ""
            if not values[value]:
                input_msg = f"{descriptions[value]} : "
            else:
                input_msg = f"{descriptions[value]} [{values[value]}] : "
            while not new_params[param][value]:
                input_var = input(input_msg)
                if not input_var:
                    new_params[param][value] = values[value]
                else:
                    new_params[param][value] = input_var
    print(new_params)
    with open(config_fname, 'w', encoding='utf-8') as fp:
        toml.dump(new_params, fp)
    return new_params


def load_params(fname=config_fname, param=""):
    """
    Load parameters from file.

    If config file doesn't exist, we ask user to build one
    """
    params = {}
    if not os.path.isfile(fname):
        print()
        params = my_setup()

    if not params:
        with open(fname, 'r', encoding='utf-8') as fp:
            params.update(toml.load(fp))

    if param:
        return params[param]
    else:
        return params


if __name__ == '__main__':
    # jeszcze nie uwzgledniam w mainie load_params() ani my_setup(), nawet nie wiem czy sa dobrze napisane
    tptp_file = os.path.join(cwd, 'tests/data/test.p')
    # command = f"tptp_to_ladr < {tptp_file} | prover9 > {cwd}/tests/ladr_file.out"
    # print(command.split(), end='')
    # print(subprocess.check_call(command.split()))
    # subprocess.Popen(command.split())
    # subprocess.call(command.split()) #Popen ani call nie dzialaja, czemu?
    # os.system(command)
