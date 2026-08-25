import api from '@/lib/api'
import type {
  CostLogRequest,
  CostLogEntry,
  MissionCostsResponse,
  MissionPnlResponse,
} from '@/types'

export async function fetchMissionCosts(missionId: string): Promise<MissionCostsResponse> {
  const res = await api.get<MissionCostsResponse>(`/api/v1/missions/${missionId}/costs`)
  return res.data
}

export async function fetchMissionPnl(missionId: string): Promise<MissionPnlResponse> {
  const res = await api.get<MissionPnlResponse>(`/api/v1/missions/${missionId}/pnl`)
  return res.data
}

export async function logLegCost(
  missionId: string,
  legNumber: number,
  data: CostLogRequest,
): Promise<CostLogEntry> {
  const res = await api.post<CostLogEntry>(
    `/api/v1/missions/${missionId}/legs/${legNumber}/costs`,
    data,
  )
  return res.data
}
