using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Linq;

public class YoloCaptureManager : MonoBehaviour
{
    [Header("🎥 YOLO 캡처 설정")]
    public Camera[] yoloCameras;
    public int imageWidth = 1920;
    public int imageHeight = 1080;
    public float captureInterval = 1f;
    public int targetImageCount = 5000;
    public bool stopAtTarget = false;

    [Header("🎯 정밀 바운딩 박스 설정")]
    [Range(0.05f, 0.25f)]
    public float maxBoundingBoxWidth = 0.15f;  // 최대 폭 15%
    [Range(0.05f, 0.20f)]
    public float maxBoundingBoxHeight = 0.12f; // 최대 높이 12%
    public bool enablePreciseBoundingBox = true; // 정밀 바운딩 박스 활성화
    public bool enableDebugLogs = false; // 디버그 로그 활성화

    [System.Serializable]
    public class TagClassMapping
    {
        public string tag;
        public int classId;
        public string className;
    }

    public List<TagClassMapping> tagClassMappings = new List<TagClassMapping>
    {
        new TagClassMapping { tag = "Bird", classId = 0, className = "Bird" },
        new TagClassMapping { tag = "Airplane", classId = 1, className = "Airplane" },
        new TagClassMapping { tag = "FOD", classId = 2, className = "FOD" },
        new TagClassMapping { tag = "Animal", classId = 3, className = "Animal" },
        new TagClassMapping { tag = "Fire", classId = 5, className = "Fire" },
        new TagClassMapping { tag = "Car", classId = 6, className = "Car" },
        new TagClassMapping { tag = "Person", classId = 7, className = "Person" }
    };

    private int frameIndex = 0;
    private int totalCapturedImages = 0;
    private Coroutine captureCoroutine;

    void Start()
    {
        Debug.Log($"🎯 정밀 바운딩 박스: {(enablePreciseBoundingBox ? "활성화" : "비활성화")}");
        Debug.Log($"📊 바운딩 박스 한계: W≤{maxBoundingBoxWidth*100:F0}%, H≤{maxBoundingBoxHeight*100:F0}%");
        StartCapture();
    }

    public void StartCapture()
    {
        if (captureCoroutine != null) return;
        captureCoroutine = StartCoroutine(CaptureLoop());
        Debug.Log("🎬 YOLO 캡처 시작");
    }

    public void StopCapture()
    {
        if (captureCoroutine != null)
        {
            StopCoroutine(captureCoroutine);
            captureCoroutine = null;
        }
        Debug.Log("🛑 YOLO 캡처 중지");
    }

    IEnumerator CaptureLoop()
    {
        while (true)
        {
            CaptureAndLabelForYOLO(frameIndex);
            totalCapturedImages += yoloCameras.Length;
            frameIndex++;

            if (stopAtTarget && totalCapturedImages >= targetImageCount)
                break;

            yield return new WaitForSeconds(captureInterval);
        }
    }

    public void CaptureAndLabelForYOLO(int index)
    {
        foreach (Camera cam in yoloCameras)
        {
            CaptureImage(cam, index);
            GenerateYOLOLabel(cam, index);
        }
    }

    void CaptureImage(Camera cam, int index)
    {
        string dir = GetCameraPath(cam);
        Directory.CreateDirectory(dir);
        string path = Path.Combine(dir, $"frame_{index:D5}.png");

        RenderTexture rt = new RenderTexture(imageWidth, imageHeight, 24);
        cam.targetTexture = rt;
        Texture2D tex = new Texture2D(imageWidth, imageHeight, TextureFormat.RGB24, false);

        cam.Render();
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, imageWidth, imageHeight), 0, 0);
        tex.Apply();

        cam.targetTexture = null;
        RenderTexture.active = null;
        Destroy(rt);

        File.WriteAllBytes(path, tex.EncodeToPNG());
    }

    void GenerateYOLOLabel(Camera cam, int index)
    {
        string dir = GetCameraPath(cam);
        Directory.CreateDirectory(dir);
        string path = Path.Combine(dir, $"frame_{index:D5}.txt");

        var sb = new StringBuilder();

        foreach (var mapping in tagClassMappings)
        {
            sb.Append(GenerateClassLabels(cam, mapping.tag, mapping.classId));
        }

        File.WriteAllText(path, sb.ToString());
    }

    string GenerateClassLabels(Camera cam, string tag, int classId)
    {
        StringBuilder sb = new StringBuilder();
        var objects = GameObject.FindGameObjectsWithTag(tag);
        
        int validBoxes = 0;
        int invalidBoxes = 0;
        int outOfFrustumBoxes = 0;
        int tooSmallBoxes = 0;

        if (enableDebugLogs)
        {
            string objectNames = string.Join(", ", objects.Select(o => $"'{o.name}'"));
            Debug.Log($"[DETECTION] {tag} - Found {objects.Length} objects: [{objectNames}]");
        }

        foreach (var obj in objects)
        {
            // 🚫 관리 객체들 필터링
            if (IsManagerObject(obj.name))
            {
                continue;
            }
            
            // 🎯 정밀 바운딩 박스 vs 기존 방식 선택
            if (enablePreciseBoundingBox)
            {
                string label = GeneratePreciseBoundingBox(cam, obj, tag, classId);
                if (!string.IsNullOrEmpty(label))
                {
                    sb.Append(label);
                    validBoxes++;
                }
                else
                {
                    invalidBoxes++;
                }
            }
            else
            {
                // 기존 간단한 방식
                string label = GenerateSimpleBoundingBox(cam, obj, tag, classId);
                if (!string.IsNullOrEmpty(label))
                {
                    sb.Append(label);
                    validBoxes++;
                }
                else
                {
                    invalidBoxes++;
                }
            }
        }

        if (enableDebugLogs)
        {
            Debug.Log($"[YOLO] {tag} - Valid: {validBoxes}, Invalid: {invalidBoxes}, OutOfFrustum: {outOfFrustumBoxes}, TooSmall: {tooSmallBoxes}");
        }

        return sb.ToString();
    }

    /// <summary>
    /// 🎯 정밀한 8방향 투영 바운딩 박스 계산 (모든 객체 동일 방식)
    /// </summary>
    string GeneratePreciseBoundingBox(Camera cam, GameObject obj, string tag, int classId)
    {
        // 🎯 중심점 계산: 실제 렌더링되는 영역의 중심 사용
        Bounds bounds = GetCombinedBounds(obj);
        Vector3 centerWorld = bounds.size != Vector3.zero ? bounds.center : obj.transform.position;
        
        Vector3 screenCenter = cam.WorldToScreenPoint(centerWorld);
        
        if (screenCenter.z <= 0f)
        {
            if (enableDebugLogs) Debug.Log($"[SKIP-BEHIND] {tag} '{obj.name}' - Behind camera");
            return "";
        }

        // 🎯 8코너 투영 방식으로 바운딩 박스 계산
        var boundingBox = Calculate8CornerBoundingBox(cam, obj, bounds);
        if (!boundingBox.HasValue)
        {
            if (enableDebugLogs) Debug.Log($"[SKIP-CALC-FAIL] {tag} '{obj.name}' - Bounding box calculation failed");
            return "";
        }

        float centerX = boundingBox.Value.centerX;
        float centerY = boundingBox.Value.centerY;
        float boxWidth = boundingBox.Value.width;
        float boxHeight = boundingBox.Value.height;

        // 최소/최대 크기 제한만 적용
        boxWidth = Mathf.Clamp(boxWidth, 0.005f, maxBoundingBoxWidth);
        boxHeight = Mathf.Clamp(boxHeight, 0.005f, maxBoundingBoxHeight);

        // 🎯 바운딩 박스 영역의 20% 이상이 화면에 보이는지 체크
        float visibilityRatio = CalculateVisibilityRatio(centerX, centerY, boxWidth, boxHeight);
        if (visibilityRatio < 0.2f) // 20% 미만이면 제외
        {
            if (enableDebugLogs) Debug.Log($"[SKIP-LOW-VISIBILITY] {tag} '{obj.name}' - Visibility: {visibilityRatio*100:F1}% < 20%");
            return "";
        }

        if (enableDebugLogs)
        {
            Debug.Log($"[PRECISE-BBOX] {tag} '{obj.name}' - Center({centerX:F6}, {centerY:F6}) Size({boxWidth:F6}x{boxHeight:F6}) Visibility: {visibilityRatio*100:F1}%");
        }

        return $"{classId} {centerX:F6} {centerY:F6} {boxWidth:F6} {boxHeight:F6}\n";
    }

    /// <summary>
    /// 바운딩 박스가 화면에 보이는 비율 계산
    /// </summary>
    float CalculateVisibilityRatio(float centerX, float centerY, float width, float height)
    {
        // 바운딩 박스의 경계 계산
        float left = centerX - width / 2f;
        float right = centerX + width / 2f;
        float top = centerY - height / 2f;
        float bottom = centerY + height / 2f;

        // 화면과 교차하는 영역 계산
        float visibleLeft = Mathf.Max(left, 0f);
        float visibleRight = Mathf.Min(right, 1f);
        float visibleTop = Mathf.Max(top, 0f);
        float visibleBottom = Mathf.Min(bottom, 1f);

        // 보이는 영역이 있는지 확인
        if (visibleRight <= visibleLeft || visibleBottom <= visibleTop)
        {
            return 0f; // 전혀 보이지 않음
        }

        // 보이는 영역과 전체 영역의 비율 계산
        float visibleArea = (visibleRight - visibleLeft) * (visibleBottom - visibleTop);
        float totalArea = width * height;

        return totalArea > 0 ? visibleArea / totalArea : 0f;
    }

    /// <summary>
    /// 바운딩 박스 결과 구조체
    /// </summary>
    struct BoundingBoxResult
    {
        public float centerX, centerY, width, height;
    }

    /// <summary>
    /// 🎯 8코너 투영 방식 바운딩 박스 계산 (단순화)
    /// </summary>
    BoundingBoxResult? Calculate8CornerBoundingBox(Camera cam, GameObject obj, Bounds bounds)
    {
        if (bounds.size == Vector3.zero)
        {
            // 바운드가 없으면 Transform 위치 기준으로 기본 크기 사용
            Vector3 screenCenter = cam.WorldToScreenPoint(obj.transform.position);
            if (screenCenter.z <= 0) return null;
            
            return new BoundingBoxResult
            {
                centerX = screenCenter.x / imageWidth,
                centerY = 1f - (screenCenter.y / imageHeight),
                width = 0.05f,  // 기본 크기
                height = 0.05f
            };
        }

        Vector3[] corners = GetBoundsCorners(bounds);
        float minX = float.MaxValue, maxX = float.MinValue;
        float minY = float.MaxValue, maxY = float.MinValue;
        int validCorners = 0;

        foreach (var corner in corners)
        {
            Vector3 screenCorner = cam.WorldToScreenPoint(corner);
            if (screenCorner.z > 0) // 카메라 앞에 있는 점만 사용
            {
                float normalizedX = screenCorner.x / imageWidth;
                float normalizedY = 1f - (screenCorner.y / imageHeight);
                
                minX = Mathf.Min(minX, normalizedX);
                maxX = Mathf.Max(maxX, normalizedX);
                minY = Mathf.Min(minY, normalizedY);
                maxY = Mathf.Max(maxY, normalizedY);
                validCorners++;
            }
        }

        if (validCorners < 2) // 최소 2개 코너만 보여도 OK
        {
            return null;
        }

        float width = maxX - minX;
        float height = maxY - minY;

        // 너무 작으면 최소 크기 보장
        if (width < 0.01f) width = 0.01f;
        if (height < 0.01f) height = 0.01f;

        return new BoundingBoxResult
        {
            centerX = (minX + maxX) / 2f,
            centerY = (minY + maxY) / 2f,
            width = width,
            height = height
        };
    }

    /// <summary>
    /// 기존 간단한 바운딩 박스 계산 (호환성 유지)
    /// </summary>
    string GenerateSimpleBoundingBox(Camera cam, GameObject obj, string tag, int classId)
    {
        Renderer rend = obj.GetComponentInChildren<Renderer>();
        if (rend == null) return "";

        Bounds bounds = rend.bounds;
        Vector3 worldCenter = bounds.center;
        Vector3 screenCenter = cam.WorldToScreenPoint(worldCenter);

        if (screenCenter.z <= 0f) return "";

        float x = screenCenter.x / imageWidth;
        float y = 1f - (screenCenter.y / imageHeight);

        float depth = screenCenter.z;
        float worldWidth = bounds.size.x;
        float worldHeight = bounds.size.y;

        float pixelPerUnit = (imageHeight / (2.0f * Mathf.Tan(0.5f * cam.fieldOfView * Mathf.Deg2Rad))) / depth;

        float w = (worldWidth * pixelPerUnit) / imageWidth;
        float h = (worldHeight * pixelPerUnit) / imageHeight;

        w = Mathf.Clamp(w, 0.005f, 0.5f);
        h = Mathf.Clamp(h, 0.005f, 0.5f);

        if (x >= -0.1f && x <= 1.1f && y >= -0.1f && y <= 1.1f)
        {
            return $"{classId} {x:F6} {y:F6} {w:F6} {h:F6}\n";
        }

        return "";
    }

    /// <summary>
    /// 관리 객체인지 확인
    /// </summary>
    bool IsManagerObject(string objectName)
    {
        string[] managerNames = {
            "BirdSpawner", "AirplaneManager", "AIrplaneManager"
        };
        
        return System.Array.Exists(managerNames, name => 
            objectName.Equals(name, System.StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>
    /// 바운딩 박스의 8개 모서리 좌표 계산
    /// </summary>
    Vector3[] GetBoundsCorners(Bounds bounds)
    {
        Vector3[] corners = new Vector3[8];
        Vector3 center = bounds.center;
        Vector3 size = bounds.size * 0.5f;
        
        corners[0] = center + new Vector3(-size.x, -size.y, -size.z);
        corners[1] = center + new Vector3(+size.x, -size.y, -size.z);
        corners[2] = center + new Vector3(-size.x, +size.y, -size.z);
        corners[3] = center + new Vector3(+size.x, +size.y, -size.z);
        corners[4] = center + new Vector3(-size.x, -size.y, +size.z);
        corners[5] = center + new Vector3(+size.x, -size.y, +size.z);
        corners[6] = center + new Vector3(-size.x, +size.y, +size.z);
        corners[7] = center + new Vector3(+size.x, +size.y, +size.z);
        
        return corners;
    }

    /// <summary>
    /// 결합된 바운드 계산
    /// </summary>
    Bounds GetCombinedBounds(GameObject go)
    {
        Renderer[] renderers = go.GetComponentsInChildren<Renderer>();
        if (renderers.Length == 0) return new Bounds();

        Bounds bounds = renderers[0].bounds;
        for (int i = 1; i < renderers.Length; i++)
        {
            bounds.Encapsulate(renderers[i].bounds);
        }
        return bounds;
    }

    string GetCameraPath(Camera cam)
    {
        string root = Path.Combine(Application.dataPath, "../data/yolo_capture");
        return Path.Combine(root, cam.name);
    }
}