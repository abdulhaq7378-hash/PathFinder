import sys, numpy as np
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); from evaluate import load, associate, umeyama
def qmat(q):  # q = x y z w
    x,y,z,w = q.T
    return np.stack([1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y), 2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x), 2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)],1).reshape(-1,3,3)
te,pe,qe = load(sys.argv[1]); tg,pg,qg = load(sys.argv[2])
ie,ig = associate(te,tg); te,pe,qe,pg,qg = te[ie],pe[ie],qe[ie],pg[ig],qg[ig]
Re, Rg = qmat(qe), qmat(qg)
# tilt error: angle between body 'up' predicted (R^T z) for est vs gt
ue = Re[:,2,:]; ug = Rg[:,2,:]
tilt = np.degrees(np.arccos(np.clip((ue*ug).sum(1),-1,1)))
t = te-te[0]
for s in [0,10,30,60,90,120,150,175,183]:
    k = np.searchsorted(t,s); k=min(k,len(t)-1)
    print(f"t={s:5.0f}s tilt_err={tilt[k]:6.2f}deg  est_p={pe[k].round(2)}  gt_p={pg[k].round(2)}")
vg = np.gradient(pg, te, axis=0); print("gt speed mean", np.linalg.norm(vg,axis=1).mean(), "max", np.linalg.norm(vg,axis=1).max())
print("gt pos std", pg.std(0), "est pos std", pe.std(0))
