"""Lightweight, explicit evaluation metrics; metrics do not replace listening tests."""
import math

def pitch_metrics(reference_hz, predicted_hz):
    if len(reference_hz) != len(predicted_hz): raise ValueError("F0 arrays must have equal length")
    pairs=[(float(a),float(b)) for a,b in zip(reference_hz,predicted_hz) if float(a)>0 and float(b)>0 and math.isfinite(float(a)) and math.isfinite(float(b))]
    if not pairs: return {"voiced_reference_frames":0,"f0_rmse_hz":None,"f0_mae_hz":None,"gross_error_rate_20pct":None}
    diffs=[b-a for a,b in pairs]
    gross=sum(abs(b-a)/a>0.2 for a,b in pairs)/len(pairs)
    return {"voiced_reference_frames":len(pairs),"f0_rmse_hz":round(math.sqrt(sum(d*d for d in diffs)/len(diffs)),6),"f0_mae_hz":round(sum(abs(d) for d in diffs)/len(diffs),6),"gross_error_rate_20pct":round(gross,6)}

def onset_mae_ms(reference_seconds, predicted_seconds):
    if len(reference_seconds)!=len(predicted_seconds): raise ValueError("Onset arrays must have equal length")
    if not reference_seconds: return None
    return round(sum(abs(float(a)-float(b))*1000 for a,b in zip(reference_seconds,predicted_seconds))/len(reference_seconds),6)
