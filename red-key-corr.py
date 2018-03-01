#!/usr/bin/python3
# coding=UTF-8

from tkinter import *
from tkinter import filedialog
from tkinter.messagebox import showerror
from string import hexdigits
import os.path
import json

SETTINGS_FILE = 'settings.json'

RED_KEY_ADD = 0xCF  # red key address in flash memory
RED_KEY_LEN = 4  # red key length in bytes


class Gui(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title('Изменение красного ключа')
        self.resizable(0, 0)

        # Load default settings if settings file exists
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE) as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

        # Create widget
        self.red_key = StringVar()
        self.hex_file = StringVar()
        self.new_hex_file = StringVar()

        self.red_key.set(self.settings['red_key'] if 'red_key' in self.settings else '')
        self.hex_file.set(self.settings['hex_file'] if 'hex_file' in self.settings else '')

        Label(self, text='HEX-файл:', width=25, anchor=E).grid()
        Entry(self, textvariable=self.hex_file, width=60).grid(row=0, column=1)
        Button(self, text='Открыть...',
               command=(lambda: self.file_open(self.hex_file, ('HEX-файл', '*.hex')))).grid(row=0, column=2)

        Label(self, text='Новый ИД красного ключа:', width=25, anchor=E).grid(row=1, column=0)
        Entry(self, textvariable=self.red_key, width=10).grid(row=1, column=1, sticky='W')

        Button(self, text='Сохранить HEX-файл с новым ИД как...', command=self.do).grid(row=4, column=1, sticky='W')

        # Save settings before closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    @staticmethod
    def file_open(var, filetype):
        file = filedialog.askopenfile(filetypes=(filetype, ('все файлы', '*.*'))).name
        if file:
            var.set(file)

    @staticmethod
    def read_hexline(line, strict_check_sum=True):
        data_len = int(line[1:3], 16)
        address_msb, address_lsb = int(line[3:5], 16), int(line[5:7], 16)
        address = address_msb * 256 + address_lsb
        record_type = int(line[7:9], 16)
        data = bytes(int(line[9+i*2:11+i*2], 16) for i in range(data_len))
        check_sum = int(line[9+data_len*2:11+data_len*2], 16)
        check_sum_actual = (~((data_len+address_msb+address_lsb+record_type+sum(data)) & 0x00FF) + 1) & 0xFF
        if check_sum != check_sum_actual:
            if strict_check_sum:
                sys.stdout.write("Incorrect check sum in HEX-file\nline: "
                                 "\"{0}\"\ncalculated check sum: {1}\n"
                                 "check sum in file: {2}".format(line.strip(), check_sum_actual, check_sum))
                raise ValueError()
        return {"data_len": data_len, "address": address, "record_type": record_type, "data": data,
                "check_sum_actual": check_sum_actual, "check_sum" : check_sum}

    @staticmethod
    def check_hex_value(s, num_digits=-1):
        if len(s) == num_digits or (num_digits == -1 and len(s) > 0):
            for c in s:
                if c not in hexdigits:
                    return False
            return True
        else:
            return False

    def do(self):
        # Check if input file exists
        if not os.path.isfile(self.hex_file.get()):
            showerror(message="Файла \"{0}\" не существует".format(self.hex_file.get()))
            return
        else:
            self.settings['hex_file'] = self.hex_file.get()

        # Verify specified red key ID
        red_key_id = self.red_key.get().strip()
        if not self.check_hex_value(red_key_id, num_digits=8):
            showerror(message="Требуется ИД красного ключа в формате HHHHHHHH, где H - шестнадцатеричная цифра")
            return
        else:
            self.settings['red_key'] = self.red_key.get()

        # Ask output file name
        new_hex_file = filedialog.asksaveasfilename(filetypes=(('hex-файл', '*.hex'), ('все файлы', '*.*')))
        if new_hex_file:
            nhf = open(new_hex_file, 'w')
        else:
            return

        # Read line-by-line input hex and write it out with red key has replaced
        with open(self.hex_file.get()) as hf:
            for line in hf.readlines():
                parsed_hexline = self.read_hexline(line)  # parse hex line to find out hex address and hex record type

                # If record with data
                if parsed_hexline["record_type"] == 0x00:
                    # If record includes red key bytes
                    if (RED_KEY_ADD <= parsed_hexline["address"] + parsed_hexline["data_len"] - 1 and
                            parsed_hexline["address"] <= RED_KEY_ADD + RED_KEY_LEN - 1):
                        # Calc index of the first character containing red key bytes
                        col_beg = 9 + (RED_KEY_ADD - parsed_hexline["address"] if RED_KEY_ADD >= parsed_hexline["address"]
                                       else 0) * 2
                        # Calc index of the last character containing red key bytes
                        col_end = 9 + (RED_KEY_ADD + RED_KEY_LEN - 1 - parsed_hexline["address"]
                                       if RED_KEY_ADD + RED_KEY_LEN < parsed_hexline["address"] +  parsed_hexline["data_len"] - 1
                                       else parsed_hexline["data_len"] - 1) * 2 + 1
                        # Calc index of the first character in red_key_id met in hex record
                        col_red_key_beg = 0 if RED_KEY_ADD >= parsed_hexline["address"]\
                                          else (parsed_hexline["address"] - RED_KEY_ADD) * 2
                        # Calc index of the last character in red_key_id met in hex record
                        col_red_key_end = col_red_key_beg + col_end - col_beg
                        # Compile new hex line with new red key
                        line = line[:col_beg] + red_key_id[col_red_key_beg:(col_red_key_end + 1)] + line[(col_end + 1):]
                        # Recalculate check sum
                        new_parsed_hex_line = self.read_hexline(line, strict_check_sum=False)
                        # Insert corrected check sum
                        line = line[:-3] + (hex(new_parsed_hex_line["check_sum_actual"] + 0x100)[-2:]).upper() + '\n'

                nhf.write(line)  # write line out

        nhf.close()  # Close output hex file

    def on_closing(self):
        with open(SETTINGS_FILE, 'w') as file:
            json.dump(self.settings, file)
        self.destroy()


if __name__ == '__main__':
    top = Gui()
    top.mainloop()
