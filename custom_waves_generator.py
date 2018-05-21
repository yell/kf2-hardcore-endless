#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import yaml
import os.path


class KF2_ZED(object):
    # small zeds
    Clot = 'Clot_Alpha'
    Rioter = 'Clot_AlphaKing'
    AlphaClot = 'Clot_Alpha_Versus'
    Cyst = 'Clot_Cyst'
    Slasher = 'Clot_Slasher'
    AlphaSlasher = 'Clot_Slasher_Versus'

    Crawler = 'Crawler'
    EliteCrawler = 'CrawlerKing'
    AlphaCrawler = 'Crawler_Versus'
    Stalker = 'Stalker'
    AlphaStalker = 'Stalker_Versus'
    Gorefast = 'Gorefast'
    AlphaGorefast = 'Gorefast_Versus'

    # medium
    Gorefiend = 'GorefastDualBlade'
    Bloat = 'Bloat'
    AlphaBloat = 'Bloat_Versus'
    Siren = 'Siren'
    AlphaSiren = 'Siren_Versus'
    Husk = 'Husk'
    AlphaHusk = 'Husk_Versus'
    Quarterpound = FPMini = MiniFP = FleshpoundMini = MiniFleshpound = 'FleshpoundMini'

    # large
    Scrake = 'Scrake'
    AlphaScrake = 'Scrake_Versus'
    Fleshpound = 'Fleshpound'
    AlphaFleshpound = 'Fleshpound_Versus'

    # bosses
    Patriarch = 'Patriarch'
    AlphaPatriarch = 'Patriarch_Versus'
    Hans = 'Hans'
    KingFP = FleshpoundKing = KingFleshpound = 'FleshpoundKing'
    Abomination = KingBloat = BloatKing = 'BloatKing'

    @staticmethod
    def to_str(zed):
        return 'KFGameContent.KFPawn_Zed' + str(zed)

Z = KF2_ZED


class KF2_EndlessUtility(object):
    """
    Numbers as per 1.5.2018

    References
    ----------
    * https://wiki.tripwireinteractive.com/index.php?title=Endless_Mode
    """
    @staticmethod
    def is_valid_num_wave(num_wave):
        return isinstance(num_wave, int) and 1 <= num_wave <= 254

    @staticmethod
    def is_valid_n_players(n_players):
        return isinstance(n_players, int) and 1 <= n_players <= 6

    @staticmethod
    def is_boss_wave(num_wave):
        assert KF2_EndlessUtility.is_valid_num_wave(num_wave)
        return num_wave % 5 == 0

    @staticmethod
    def _base_number_of_zeds(num_wave):
        if KF2_EndlessUtility.is_boss_wave(num_wave):
            return 0
        if num_wave < 10:
            return {1: 25, 2: 28, 3: 32, 4: 32, 6: 35, 7: 35, 8: 35, 9: 40}[num_wave]
        return 42 #  `num_wave` >= 11

    @staticmethod
    def base_number_of_zeds(num_wave):
        assert KF2_EndlessUtility.is_valid_num_wave(num_wave)
        return KF2_EndlessUtility._base_number_of_zeds(num_wave)

    @staticmethod
    def _wave_length_modifier(n_players):
        return {1: 1, 2: 2, 3: 2.75, 4: 3.5, 5: 4, 6: 5}[n_players]

    @staticmethod
    def wave_length_modifier(n_players):
        assert KF2_EndlessUtility.is_valid_n_players(n_players)
        return KF2_EndlessUtility._wave_length_modifier(n_players)

    @staticmethod
    def _wave_count_mod_hoe(num_wave):
        if num_wave <= 25:
            return {0: 0.85, 1: 0.9, 2: 0.95, 3: 1., 4: 1.05}[(num_wave - 1)/5]
        return 1.15 + 0.1 * ((num_wave - 26)/5)

    @staticmethod
    def wave_count_mod(num_wave, difficulty='hoe'):
        assert KF2_EndlessUtility.is_valid_num_wave(num_wave)
        assert difficulty == 'hoe'
        return KF2_EndlessUtility._wave_count_mod_hoe(num_wave)
        
    @staticmethod
    def n_zeds(num_wave, n_players, difficulty='hoe'):
        n = KF2_EndlessUtility.base_number_of_zeds(num_wave) *\
            KF2_EndlessUtility.wave_length_modifier(n_players) *\
            KF2_EndlessUtility.wave_count_mod(num_wave, difficulty)
        return int(n)

    @staticmethod
    def _spawn_rate_modifier_hoe(num_wave):
        if num_wave <= 30:
            return {0: 0.68, 1: 0.65, 2: 0.6, 3: 0.55, 4: 0.5, 5: 0.2}[(num_wave - 1)/5]
        return 0.

    @staticmethod
    def spawn_delay(base_spawn_delay, num_wave):
        assert base_spawn_delay > 0
        assert KF2_EndlessUtility.is_valid_num_wave(num_wave)
        return max(1., KF2_EndlessUtility._spawn_rate_modifier_hoe(num_wave) * base_spawn_delay)

KF2 = KF2_EndlessUtility


def make_line_interp((x0, y0), (x1, y1)):
    assert x1 != x0
    def f(x):
        return (y1 - y0) * (x - x0) / (x1 - x0) + y0
    return f


def make_line_const_interp((x0, y0), (x1, y1)):
    """Same as `make_line_interp`, but extrapolated constantly beyond [x0; x1]."""
    m = min(x0, x1)
    M = max(x0, x1)
    def f(x):
        return make_line_interp((x0, y0), (x1, y1))(M if x > M else m if x < m else x)
    return f


class CustomWavesGenerator(object):
    """
    Class encapsulating custom zeds waves
    """
    def __init__(self, zeds_config=None):
        self.zeds_config = zeds_config or {}

        self.zeds_config.setdefault('n_players', 6)
        self.zeds_config.setdefault('difficulty', 'hoe')
        self.zeds_config.setdefault('zed_multiplier', 1.0)
        self.zeds_config.setdefault('custom_zeds_ratio_policy', lambda n: 1.0)

        self.zeds_config.setdefault('spawn_at_once', 1)
        self.zeds_config.setdefault('probability', 0.5)
        self.zeds_config.setdefault('spawn_delay', 15.0)
        self.zeds_config.setdefault('ratio', 0.0)
        self.zeds_config.setdefault('number', 0)
        self.zeds_config.setdefault('n_generators', 1)
        self.ZED_OPTIONS = ['spawn_at_once', 'probability', 'spawn_delay', 'ratio', 'number', 'n_generators']

        self.zeds_config.setdefault('zeds_register', [])

        for attr in self.zeds_config.keys():
            setattr(self, attr, self.zeds_config[attr])

        self.t = 'CustomZeds=(Wave={num_wave},SpawnAtOnce={spawn_at_once},Zed="{zed}",'
        self.t += 'Probability={probability},Delay={spawn_delay},MaxSpawns={max_zeds})'

    def print_waves(self, markdown=False):
        # collect all names
        names = []
        for zeds_register_wave in self.zeds_register:
            num_wave = zeds_register_wave['num_wave']
            if 'name' in zeds_register_wave:
                names.append((num_wave, zeds_register_wave['name']))
        names.sort()

        # print (in the markdown format if needed)
        if markdown:
            print '| Wave | <div align="center">Name</div> |'
            print '| :---: | :--- |'

        for num_wave, name in names:
            if markdown:
                print '| **{0}** | "{1}" |'.format(num_wave, name)
            else:
                print 'Wave {0}: "{1}"'.format(num_wave, name)

    def to_ini(self, filename='kfzedvarient.ini'):
        s_list = []
        s_list.append('[ZedVarient.ZedVarient]')
        s_list.append('ZedMultiplier={0:.6f}'.format(self.zed_multiplier))
        s_list.append('bConfigsInit=True')

        for i, zeds_register_wave in enumerate(self.zeds_register):
            # set wave-specific options to the global defaults
            for option in self.ZED_OPTIONS:
                zeds_register_wave.setdefault(option, self.zeds_config[option])
            
            zeds_register_wave.setdefault('num_wave', i + 1)
            num_wave = zeds_register_wave['num_wave']

            # get or estimate (actual) total number of zeds
            n_zeds_f = 0.
            if KF2.is_boss_wave(num_wave):
                n_zeds_f = 0.5 * ( KF2.n_zeds(num_wave - 1, self.n_players, self.difficulty) +
                                   KF2.n_zeds(num_wave + 1, self.n_players, self.difficulty) )
            else:
                n_zeds_f = KF2.n_zeds(num_wave, self.n_players, self.difficulty)
            n_zeds_f *= self.zed_multiplier

            # estimate number of custom zeds
            n_custom_zeds_f = self.custom_zeds_ratio_policy(num_wave) * n_zeds_f

            # preparation loop
            sum_ratio = 0.
            sum_numbers = 0
            for zed_entry in zeds_register_wave['zeds']:

                # set zed-specific options to the wave-specific defaults    
                for option in self.ZED_OPTIONS:
                    zed_entry.setdefault(option, zeds_register_wave[option])

                # validate params
                zed_entry['spawn_at_once'] = int(zed_entry['spawn_at_once'])
                zed_entry['probability'] = float(zed_entry['probability'])
                zed_entry['spawn_delay'] = float(zed_entry['spawn_delay'])
                zed_entry['number'] = int(zed_entry['number'])
                zed_entry['ratio'] = float(zed_entry['ratio'])
                zed_entry['n_generators'] = int(zed_entry['n_generators'])
                zed_entry['zed'] = Z.to_str(getattr(Z, zed_entry['zed']))

                # and sum all ratios and numbers for proper normalization
                sum_ratio += zed_entry['ratio']
                sum_numbers += zed_entry['number']

            # main loop
            for zed_entry in zeds_register_wave['zeds']:

                # compute max number for a particular zed
                max_zeds_f = 0.0
                if zed_entry['ratio'] > 0.0:
                    max_zeds_f = (n_custom_zeds_f - sum_numbers) * zed_entry['ratio'] / sum_ratio
                else:
                    max_zeds_f = float(zed_entry['number'])                    
                max_zeds = int(0.5 + max_zeds_f / float(zed_entry['n_generators']))

                # correct `spawn_at_once` if needed
                zed_entry['spawn_at_once'] = min(max_zeds, zed_entry['spawn_at_once'])
                
                # undo multiplication by spawn delay multiplier, which decays too quickly
                zed_entry['spawn_delay'] *= ( KF2.spawn_delay(zed_entry['spawn_delay'], 1) /
                                              KF2.spawn_delay(zed_entry['spawn_delay'], num_wave) )

                # generate config lines
                for _ in xrange(zed_entry['n_generators']):
                    s = self.t.format(num_wave=num_wave, max_zeds=max_zeds, **zed_entry)
                    s_list.append((num_wave, s))

        # sort and produce final string
        s_list[3:] = [s for i, s in sorted(s_list[3:])]
        s = '\n'.join(s_list)

        # save to ini file
        with open(filename, 'w') as f:
            f.write(s + '\n')

        return s


def main(config_filepath):
    """
    Parameters
    ----------
    config_filepath : str
        path to zeds config
    """
    dirpath, _ = os.path.split(config_filepath)
    if not dirpath: head = '.'
    if not dirpath.endswith('/'): dirpath += '/'

    # load config
    zeds_config = yaml.load(open(config_filepath, 'r'))

    # validate ratio policy
    f = globals()[zeds_config['custom_zeds_ratio_policy']]
    zeds_config['custom_zeds_ratio_policy'] = f(*zeds_config['custom_zeds_ratio_policy_params'])

    # generate ini file
    g = CustomWavesGenerator(zeds_config)
    g.print_waves()
    g.to_ini(os.path.join(dirpath, 'kfzedvarient.ini'))


if __name__ == '__main__':
    main(sys.argv[1])
