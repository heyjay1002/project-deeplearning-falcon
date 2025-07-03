using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class CameraRandomizer : MonoBehaviour
{
    [System.Serializable]
    public class CenterTargetPair
    {
        public Vector3 center;
        public Transform lookTarget;
    }

    [Header("📷 관리할 카메라들")]
    public Camera[] managedCameras;

    [Header("🗺 중심점 + 타겟 세트")]
    public List<CenterTargetPair> centerTargets = new List<CenterTargetPair>();

    [Header("📐 랜덤 위치 범위")]
    public Vector3 range = new Vector3(30, 10, 30);

    [Header("🎯 타겟 오프셋")]
    public Vector3 lookOffset = new Vector3(0, 50f, 0);

    [Header("⏱ 주기 설정")]
    public float changeInterval = 5f;
    public bool randomizeOnStart = true;
    public bool useSmoothMovement = false;
    public float smoothMoveSpeed = 2f;

    private Vector3 currentCenter;
    private Transform currentLookTarget;
    private Vector3[] targetPositions;
    private Coroutine smoothMoveCoroutine;

    void Start()
    {
        if (managedCameras == null || managedCameras.Length == 0)
        {
            Debug.LogWarning("[CameraRandomizer] 카메라 배열이 비어 있음");
            enabled = false;
            return;
        }

        if (centerTargets == null || centerTargets.Count == 0)
        {
            Debug.LogError("[CameraRandomizer] 중심점+타겟 세트가 설정되지 않음");
            enabled = false;
            return;
        }

        targetPositions = new Vector3[managedCameras.Length];
        PickNewCenterAndTarget();

        if (randomizeOnStart)
        {
            RandomizeAllInstant();
        }

        InvokeRepeating(nameof(ScheduledRandomize), changeInterval, changeInterval);
    }

    void ScheduledRandomize()
    {
        PickNewCenterAndTarget();

        if (useSmoothMovement)
            RandomizeAllSmooth();
        else
            RandomizeAllInstant();
    }

    void PickNewCenterAndTarget()
    {
        int i = Random.Range(0, centerTargets.Count);
        currentCenter = centerTargets[i].center;
        currentLookTarget = centerTargets[i].lookTarget;

        Debug.Log($"[CameraRandomizer] 🎯 중심점 선택: {currentCenter}, 타겟: {(currentLookTarget != null ? currentLookTarget.name : "없음")}");
    }

    Vector3 GetRandomPosition()
    {
        return currentCenter + new Vector3(
            Random.Range(-range.x, range.x),
            Random.Range(-range.y, range.y),
            Random.Range(-range.z, range.z)
        );
    }

    public void RandomizeAllInstant()
    {
        for (int i = 0; i < managedCameras.Length; i++)
        {
            if (managedCameras[i] == null) continue;

            Vector3 pos = GetRandomPosition();
            managedCameras[i].transform.position = pos;

            if (currentLookTarget != null)
                managedCameras[i].transform.LookAt(currentLookTarget.position + lookOffset);
        }

        Debug.Log("[CameraRandomizer] 즉시 카메라 랜덤화 완료");
    }

    public void RandomizeAllSmooth()
    {
        for (int i = 0; i < managedCameras.Length; i++)
        {
            targetPositions[i] = GetRandomPosition();
        }

        if (smoothMoveCoroutine != null)
            StopCoroutine(smoothMoveCoroutine);

        smoothMoveCoroutine = StartCoroutine(SmoothMoveToTargets());
    }

    IEnumerator SmoothMoveToTargets()
    {
        Vector3[] startPositions = new Vector3[managedCameras.Length];
        for (int i = 0; i < managedCameras.Length; i++)
        {
            if (managedCameras[i] != null)
                startPositions[i] = managedCameras[i].transform.position;
        }

        float duration = 1f / smoothMoveSpeed;
        float elapsed = 0f;

        while (elapsed < duration)
        {
            float t = Mathf.SmoothStep(0f, 1f, elapsed / duration);
            for (int i = 0; i < managedCameras.Length; i++)
            {
                if (managedCameras[i] == null) continue;

                managedCameras[i].transform.position = Vector3.Lerp(startPositions[i], targetPositions[i], t);

                if (currentLookTarget != null)
                    managedCameras[i].transform.LookAt(currentLookTarget.position + lookOffset);
            }

            elapsed += Time.deltaTime;
            yield return null;
        }
    }
}
