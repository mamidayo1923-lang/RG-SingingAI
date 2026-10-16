"""Small research baseline: phoneme/pitch-conditioned log-mel predictor.

This is a trainable baseline, not a production-grade singing voice model. It needs
aligned per-frame labels and substantial clean data to learn a useful singer identity.
"""
from __future__ import annotations
import torch
from torch import nn

class SingingMelNet(nn.Module):
    def __init__(self, vocab_size: int, mel_bins: int = 80, hidden: int = 256):
        super().__init__()
        self.phoneme = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.pitch = nn.Embedding(129, 32, padding_idx=0)  # 1..128 represent MIDI 0..127; 0 is unvoiced
        self.velocity = nn.Embedding(128, 16)
        self.input = nn.Linear(64 + 32 + 16, hidden)
        self.net = nn.Sequential(nn.GELU(), nn.Conv1d(hidden, hidden, 5, padding=2), nn.GELU(),
                                 nn.Conv1d(hidden, hidden, 5, padding=2), nn.GELU(), nn.Conv1d(hidden, mel_bins, 1))
    def forward(self, phoneme_ids, midi_pitch, velocity):
        p = self.phoneme(phoneme_ids.long().clamp(0, self.phoneme.num_embeddings-1))
        m = self.pitch((midi_pitch.long()+1).clamp(0,128))
        v = self.velocity(velocity.long().clamp(0,127))
        x = self.input(torch.cat([p,m,v], dim=-1)).transpose(1,2)
        return self.net(x).transpose(1,2)
