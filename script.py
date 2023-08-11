import argparse
import os

from pypvz.utils.recover import RecoverMan
from pypvz import Config, Repository, Library, GardenMan, User


def challenge_garden(cfg, lib, friendMan):
    gardenMan = GardenMan(cfg, lib, friendMan)
    gardenMan.challenge_all(111, 228452)


def recover_zero(cfg, repo):
    recoverMan = RecoverMan(cfg, repo)
    recoverMan.recover_zero_loop(time_gap=1.5, log=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=str, help="module name")
    args = parser.parse_args()
    abs_file_dir = os.path.dirname(os.path.abspath(__file__))
    cfg = Config(os.path.join(abs_file_dir, "config/config.json"))
    # cfg = Config(os.path.join(abs_file_dir, "config/24config.json"))
    lib = Library(cfg)
    user = User(cfg)
    repo = Repository(cfg)
    if args.module == "recover":
        print("in recover_zero")
        recover_zero(cfg, repo)
    elif args.module == "challenge":
        print("in challenge_garden")
        challenge_garden(cfg, lib, user.friendMan)
    else:
        raise NotImplementedError
