import FWCore.ParameterSet.Config as cms

from PhysicsTools.PatAlgos.recoLayer0.electronPFIsolationDepositsPAT_cff import *
from PhysicsTools.PatAlgos.recoLayer0.electronPFIsolationValuesPAT_cff import *

pfElectronIsolationPATSequence = cms.Sequence(
    electronPFIsolationDepositsPATSequence +
    electronPFIsolationValuesPATSequence
    )

