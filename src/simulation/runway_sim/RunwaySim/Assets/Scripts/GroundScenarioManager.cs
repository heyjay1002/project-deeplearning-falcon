using UnityEngine;

public class GroundScenarioManager : MonoBehaviour
{
    public GroundObjectSpawner spawner;
    public CameraRandomizer cameraRandomizer;
    public YoloCaptureManager captureManager;

    [Range(1f, 10f)]
    public float cycleInterval = 3f;

    private int currentFrame = 0;

    void Start()
    {
        StartCoroutine(RunDataCollectionLoop());
    }

    private System.Collections.IEnumerator RunDataCollectionLoop()
    {
        while (true)
        {
            CleanupObjects();                     // 기존 객체 제거
            spawner.SpawnObjects();              // 새 객체 배치
            cameraRandomizer.RandomizeAllInstant(); // 카메라 위치 재배치
            captureManager.CaptureAndLabelForYOLO(currentFrame); // 이미지+라벨 생성

            currentFrame++;
            yield return new WaitForSeconds(cycleInterval);
        }
    }

    private void CleanupObjects()
    {
        string[] tagsToClear = { "Bird", "FOD", "Person", "Fire", "Animal", "Car", "Airplane" };
        foreach (string tag in tagsToClear)
        {
            var objs = GameObject.FindGameObjectsWithTag(tag);
            foreach (var obj in objs)
            {
                Destroy(obj);
            }
        }
    }
}
