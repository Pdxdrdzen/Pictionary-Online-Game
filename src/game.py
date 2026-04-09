import random
import json

class GameState:
    def __init__(self):
        self.players={}
        self.current_word=None
        self.current_drawer=None
        self.current_guesser=None
        self.scores={}
        self.game_phase="lobby"

    def add_player(self,nick,client_socket):
        self.players[nick]=client_socket
        self.scores[nick]=0
        if len(self.players)==0:
            self._start_game()
    def _start_game(self):
        nicks=list(self.players.keys())
        self.current_drawer=nicks[0]
        self.current_guesser=nicks[1]
        self.game_phase="playing"

        with open("words/words.txt","r",encoding="utf-8") as f:
            words=[line.strip() for line in f]
        self.current_word=random.choice(words)
        self._send(self.current_guesser,{"type":"word","word":self.current_word})

        self._send(self.current_guesser,{"type":"role","role":"drawer"})
        self._send(self.current_guesser,{"type":"role","role":"guesser"})

    def handle_message(self,nick,raw_msg):
        msg=json.load(raw_msg)

        if self.game_phase=="playing":
            return

        if msg["type"]=="guess" and nick ==self.current_guesser:
            if msg["payload"].lower()==self.current_guesser:
                self.scores[nick]+=1
                self._broadcast({"type":"correct","player":nick})
                self._switch_turns()
            else:
                self._send(nick,{"type": "wrong"})
        elif msg["type"]=="draw" and nick==self.current_drawer:
            self._send(self.current_guesser,msg)
    def _switch_turns(self):
        self.current_drawer,self.current_guesser=self.current_guesser,self.current_drawer
        with open("words/words.txt","r",encoding="utf-8") as f:
            words=[line.strip() for line in f]
        self.current_word=random.choice(words)
        self._send(self.current_guesser,{"type":"word","word":self.current_word})
        self._send(self.current_drawer,{"type":"role","role":"drawer"})
        self._send(self.current_guesser,{"type":"role","role":"guesser"})

    def _send(self,nick,message):
        self.players[nick].send(json.dumps(message).encode('utf-8'))

    def _broadcast(self,message):
        for sock in self.players.values():
            sock.send(json.dumps(message).encode('utf-8'))


