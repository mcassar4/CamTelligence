export interface MediaAsset {
  id: string;
  media_type: string;
  path: string;
  attributes?: Record<string, unknown>;
  created_at: string;
}

export interface PersonEvent {
  id: string;
  camera: string;
  occurred_at: string;
  frame_asset?: MediaAsset;
  crop_asset?: MediaAsset;
  score?: number;
  created_at: string;
}

export interface VehicleEvent {
  id: string;
  camera: string;
  occurred_at: string;
  frame_asset?: MediaAsset;
  crop_asset?: MediaAsset;
  score?: number;
  label: string;
  created_at: string;
}
