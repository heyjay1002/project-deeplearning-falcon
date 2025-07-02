using UnityEngine;
using System.Collections.Generic;

public class GroundObjectSpawner : MonoBehaviour
{
    public enum RotationAxis { None, X, Y, Z }

    [System.Serializable]
    public class PrefabEntry
    {
        public GameObject prefab;
        public Vector3 rotationEuler = Vector3.zero;
        public RotationAxis randomizeAxis = RotationAxis.None;
        public bool enableRandomScale = false;
    }

    [System.Serializable]
    public class SpawnGroup
    {
        public string tag;
        public List<PrefabEntry> prefabEntries;
        public int minCount = 1;
        public int maxCount = 5;
    }

    [Header("📦 객체 스폰 그룹")]
    public List<SpawnGroup> objectGroups;

    [Header("📍 스폰 영역")]
    public Vector3 spawnAreaCenter = new Vector3(90, 0, 41);
    public Vector3 spawnAreaSize = new Vector3(60, 1, 60);

    [Header("🚧 최소 간격 설정")]
    [Range(0f, 100f)]
    public float minDistance = 3f;

    public void SpawnObjects()
    {
        // 🎯 모든 객체들의 위치를 저장할 전역 리스트
        List<Vector3> allPlacedPositions = new();

        foreach (var group in objectGroups)
        {
            if (group.prefabEntries == null || group.prefabEntries.Count == 0)
            {
                Debug.LogWarning($"[Spawner] '{group.tag}' 그룹에 프리팹이 없습니다. 스킵됨.");
                continue;
            }

            int spawnCount = Random.Range(group.minCount, group.maxCount + 1);

            for (int i = 0; i < spawnCount; i++)
            {
                // 🌀 위치 후보를 여러 번 시도
                Vector3 chosenPos = Vector3.zero;
                bool foundValidPos = false;

                for (int attempt = 0; attempt < 30; attempt++)
                {
                    Vector2 offset2D = Random.insideUnitCircle * Mathf.Min(spawnAreaSize.x, spawnAreaSize.z) * 0.5f;
                    Vector3 candidatePos = spawnAreaCenter + new Vector3(offset2D.x, 0f, offset2D.y);

                    // 🎯 모든 기존 객체들과의 거리 체크 (그룹 상관없이)
                    bool isFarEnough = true;
                    foreach (var pos in allPlacedPositions)
                    {
                        if (Vector3.Distance(candidatePos, pos) < minDistance)
                        {
                            isFarEnough = false;
                            break;
                        }
                    }

                    if (isFarEnough)
                    {
                        chosenPos = candidatePos;
                        foundValidPos = true;
                        break;
                    }
                }

                if (!foundValidPos)
                {
                    Debug.LogWarning($"[Spawner] '{group.tag}' 객체 {i} - 유효한 위치를 찾지 못해 건너뜀 (전체 {allPlacedPositions.Count}개 객체와 충돌)");
                    continue;
                }

                PrefabEntry selected = group.prefabEntries[Random.Range(0, group.prefabEntries.Count)];
                if (selected.prefab == null)
                {
                    Debug.LogWarning($"[Spawner] '{group.tag}' 그룹에 null 프리팹이 포함되어 있습니다. 건너뜀.");
                    continue;
                }

                // 회전
                Vector3 finalEuler = selected.rotationEuler;
                switch (selected.randomizeAxis)
                {
                    case RotationAxis.X: finalEuler.x = Random.Range(0f, 360f); break;
                    case RotationAxis.Y: finalEuler.y = Random.Range(0f, 360f); break;
                    case RotationAxis.Z: finalEuler.z = Random.Range(0f, 360f); break;
                }
                Quaternion rotation = Quaternion.Euler(finalEuler);

                // 스폰
                GameObject obj = Instantiate(selected.prefab, chosenPos, rotation);
                obj.tag = group.tag;
                obj.name = $"{group.tag}_{i:D2}";

                // 스케일
                if (selected.enableRandomScale)
                {
                    float scale = Random.Range(1.0f, 1.5f);
                    obj.transform.localScale *= scale;
                }

                // 🎯 전역 위치 리스트에 추가 (모든 그룹의 객체들이 공유)
                allPlacedPositions.Add(chosenPos);
                
                Debug.Log($"[Spawner] ✅ {group.tag}_{i:D2} 스폰 완료 at ({chosenPos.x:F1}, {chosenPos.y:F1}, {chosenPos.z:F1}) - 총 {allPlacedPositions.Count}개 객체");
            }
        }

        Debug.Log($"[Spawner] ✅ 모든 객체 스폰 완료 - 총 {allPlacedPositions.Count}개 객체, 최소거리: {minDistance}m");
    }
}
