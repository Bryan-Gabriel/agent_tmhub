from time import sleep
import pyautogui as pg
from os import getenv
from random import randint
from threading import Thread
from subprocess import run
from datetime import datetime as dt
from winotify import Notification, audio
from termcolor import colored

def configure_pyautogui() -> None:
    pg.FAILSAFE = True
    pg.PAUSE = 1.2

class VPN:
    def __init__(self):
        configure_pyautogui()

        def running_vpn(): run(f"explorer {getenv("VPN_SHORTCUT")}")
        Thread(target=running_vpn, daemon=True).start() # Abre o VPN em paralelo

        cont_error = 0
        init = dt.now() # Inicio da busca do Login
        isVpnNonLogged = False
        while not isVpnNonLogged:
            try: isVpnNonLogged = pg.locateOnScreen("assets/vpn.png", minSearchTime=5, confidence=.9)
            except pg.ImageNotFoundException: 
                if cont_error < 4: cont_error += 1; continue
                end = dt.now(); intervalo = end - init; # Final da busca e obtem o intervalo 
                print(f"Tela de Login do VPN não encontrada, fechando | Inicio: {init.time()} - Final: {end.time()} - Tempo de Execução: {intervalo.seconds}") # Retorna o LOG caso nao encontre
                pg.hotkey("alt", "f4")
                break

        self.login(isVpnNonLogged)
        
    def login(self, isVpnNonLogged):
        if not isVpnNonLogged: return False # Caso encontre realiza o login
        pg.doubleClick(isVpnNonLogged)
        pg.press("tab")
        pg.press("tab")
        pg.write(getenv("UID"))
        pg.press("tab")
        pg.write(getenv("VPN_PWD"))
        pg.press("enter")
        return True
    
class HK:
    time_for_apointment = 15
    time_for_fault = 15
    time_for_operational_tab = 5

    def __init__(self, isOpened:bool = False) -> None:
        configure_pyautogui()

        if not isOpened:
            def running_hk(): run(getenv("HK_SHORTCUT"))
            Thread(target=running_hk, daemon=True).start() # Abre o HK em paralelo
            pg.sleep(15) # Tempo para o HK abrir

            init = dt.now() # Tempo de Inicio da Busca de Login
            count_error = 0
            foundLogin = False

            while not foundLogin:
                try: foundLogin = pg.locateOnScreen("assets/hk.png", confidence=.9) # Seta o login como TRUE case encontre a tela
                except pg.ImageNotFoundException:
                    if count_error < 5: count_error += 1; continue

                    end = dt.now(); intervalo = end - init; # Tempo final da busca e o tempo de execução
                    print(f"Tela de Login do HK não encontrada, fechando | Inicio: {init.time()} - Final: {end.time()} - Tempo de Execução: {intervalo.seconds}") # Retorna o LOG caso nao encontre
                    pg.hotkey("alt", "f4"); break
            if self.login(foundLogin): isOpened = True

    def login(self, found) -> bool:
        if not found: return False
        pg.typewrite(getenv("UID"))
        pg.press("tab")
        pg.typewrite(getenv("HK_PWD")) 
        pg.press("enter")
        return True
    
    def go_to_date_input(self, date:str, mat:str|int) -> bool:
        pg.moveTo(121, 421)
        pg.doubleClick()
        pg.press("tab")
        pg.typewrite(date)
        pg.press("tab")
        pg.write(mat)
        pg.press("tab")
        return True
        
    def pprint(self, txt: str, separator: str = '=', sp_quant: int = 100, line_quant: int = 1):
        sobra = sp_quant - len(txt)
        left_calc = sobra // 2
        right_calc = sobra - left_calc  # Absorve o 1 caractere extra caso sobra seja ímpar
        border = (separator * sp_quant + '\n') * line_quant
        print(border, end='')
        print(f"{separator * left_calc}{txt}{separator * right_calc}")
        print(border, end='')
          
    def set_adjust(self, adjusts:list = [], open_tab_moviment=False):
        # Abre a tela de Movimentação Operacional
        if open_tab_moviment: self.open_tab_moviment(); pg.sleep(self.time_for_operational_tab)
        print("Iniciando Ajustes no SAR2G - HK".center(100))
        print('\n' * 2)
        for adjust in adjusts: # Itera sobre os ajustes
            days = adjust.get("days") # Obtem os dias do colab
            mat = str(adjust.get("mat")) # Obtem a MAT/RE do Colab
            self.pprint(f"Iniciando Matricula: {mat}")

            for day in days:
                self.go_to_date_input(date=day, mat=mat)
                sleep(2)

                for task in adjust.get("tasks"):
                    print(f"Iniciando Tarefa: {colored(task.upper(), "green") if task.lower() == 'apointment' else colored(task.upper(), "red")} - Data: {dt.now().time()}")
                    match task:
                        case "cancel_fault":
                            make_task, cont, isFault = False, 0, False
                            while not isFault:
                                try: isFault = pg.locateOnScreen("assets/no_fault.png", confidence=.9); make_task = True;
                                except: 
                                    cont += 1
                                    if cont == 4: print(f"FALTA NÃO ENCONTRADA - MATRICULA: {mat} - DIA: {day} - INFO: {dt.now()}"); isFault = True; make_task = False;
                                
                            if self.cancel_fault(isFault, make_task): pg.sleep(self.time_for_fault); print(f"Tarefa concluida - {task} - Matricula - {mat} - {dt.now().time()}");

                        case "apointment":
                            make_task, cont, isApointment = False, 0, False
                            while not isApointment: 
                                try: isApointment = pg.locateOnScreen("assets/apointment.png", confidence=.9); make_task = True
                                except: 
                                    cont += 1
                                    if cont == 4: print(f"APONTAMENTO NÃO ENCONTRADO - MATRICULA: {mat} - DIA: {day} - INFO: {dt.now()}"); isApointment = True; make_task = False
                            if self.set_apointments(isApointment, make_task): pg.sleep(self.time_for_apointment); print(f"Tarefa concluida - {task} - Matricula - {mat} - {dt.now().time()}");
                    
    def open_tab_moviment(self, init:bool= True) -> bool:
        if init: pg.hotkey("alt", "m"); pg.sleep(1); pg.press("o")

        isOp = False
        while not isOp:
            try: pg.doubleClick(pg.locateOnScreen(r"assets/operacional.png", minSearchTime=10, confidence=.9)); isOp = True
            except: continue
        return isOp

    def cancel_fault(self, isFault: pg.locateOnScreen, make_task:bool) -> bool:
        pg.moveTo(isFault)
        pg.doubleClick(isFault)
        sleep(6)

        [pg.press("tab") for _ in range(4)]
        [pg.press("down") for _ in range(4)]
        [pg.press("tab") for _ in range(2)]
        [pg.press("enter") for _ in range(3)]
        return True

    def set_apointments(self, isApointment:pg.locateOnScreen, make_task:bool) -> bool:
        pg.moveTo(isApointment)
        pg.doubleClick(isApointment)
        sleep(6)

        [pg.press("tab") for _ in range(3)]

        pg.press("down")
        pg.press("tab")
        pg.press("right")
        pg.press("backspace")
        pg.typewrite(str(randint(1, 9)))

        pg.press("tab")
        pg.press("down")
        pg.press("tab")
        pg.press("right")
        pg.press("backspace")
        pg.typewrite(str(randint(1, 9)))

        [pg.press("tab") for _ in range(4)]
        pg.press("right")
        pg.press("backspace")
        pg.typewrite(str(randint(1, 9)))

        pg.press("tab")
        pg.press("down")
        [pg.press("tab") for _ in range(2)]

        pg.press("enter")
        return True  
    
    def set_liberation(self, isLiberation, type):
        if not isLiberation: return False
        pg.click(isLiberation)
        [pg.press("tab") for _ in range(3)]
        [pg.typewrite(type)]
        [pg.press("tab") for _ in range(3)]
        [pg.press("enter") for _ in range(3)]
        return True

    def set_holidays(holidays:list = []) -> bool:
        if not holidays: return False
    
    def open_tab_holiday(self, init:bool= True) -> bool:
        if init: pg.hotkey("alt", "m"); pg.sleep(1); pg.press("a")

        isHd = False
        while not isHd:
            try: pg.doubleClick(pg.locateOnScreen(r"assets/holidays.png", minSearchTime=5, confidence=.9)); isHd = True
            except: pass

        isLocalHoliday = False
        while not isLocalHoliday:
            try: pg.doubleClick(pg.locateOnScreen(r"assets/localHoliday.png", minSearchTime=5, confidence=.9)); isLocalHoliday = True
            except: pass

        isClientHoliday = False
        while not isClientHoliday:
            try: pg.doubleClick(pg.locateOnScreen(r"assets/clientHoliday.png", minSearchTime=5, confidence=.9)); isClientHoliday = True
            except: pass

        pg.typewrite("MUNICIPIO DE LONDRINA")
        pg.press("tab")
        return True

    def close(self): pg.sleep(15); pg.hotkey("alt", "f4")
    
class Notify:
    def __init__(self, 
        id="RPA - HK Soluções", title="Tarefa Concluída! 🎉", 
        msg="A automação terminou de rodar com sucesso.", duration:str="short"):

        self.super = Notification(app_id=id, title=title, msg=msg, duration=duration)
        self.super.set_audio(audio.Default, loop=False)
