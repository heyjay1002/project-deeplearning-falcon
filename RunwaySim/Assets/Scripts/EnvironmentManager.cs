using UnityEngine;

public class EnvironmentManager : MonoBehaviour
{
    [Header("🌞 환경 설정")]
    public Light directionalLight;
    public Gradient ambientLightColor;
    public Gradient directionalLightColor;
    public AnimationCurve lightAngleOverTime;

    [Range(0f, 1f)]
    public float timeOfDay = 0.5f;

    [Header("🌫️ 안개 설정")]
    public bool enableFog = false;
    public Color fogColorDay = new Color(0.7f, 0.8f, 0.9f);
    public Color fogColorNight = new Color(0.1f, 0.1f, 0.15f);
    public float fogDensityDay = 0.002f;
    public float fogDensityNight = 0.01f;

    [Header("⏱️ 자동 시간 흐름")]
    public bool autoCycle = false;
    public float cycleSpeed = 0.05f;

    [Header("⚙️ 성능 설정")]
    public bool performanceMode = true;
    [Range(0.1f, 5f)]
    public float updateInterval = 1f;

    private float lastUpdateTime = 0f;

    void Start()
    {
        if (performanceMode)
        {
            enableFog = false;
            autoCycle = false;
            updateInterval = 1f;
        }

        RenderSettings.fog = enableFog;
        ApplyLighting(timeOfDay);
        if (enableFog) ApplyFog(timeOfDay);
    }

    void Update()
    {
        if (Time.time - lastUpdateTime < updateInterval) return;
        lastUpdateTime = Time.time;

        if (autoCycle)
        {
            timeOfDay += Time.deltaTime * cycleSpeed;
            if (timeOfDay > 1f) timeOfDay -= 1f;
        }

        ApplyLighting(timeOfDay);
        if (enableFog) ApplyFog(timeOfDay);
    }

    void ApplyLighting(float t)
    {
        if (directionalLight != null)
        {
            directionalLight.color = performanceMode ? Color.white : directionalLightColor.Evaluate(t);
            float angle = performanceMode ? 50f : Mathf.Lerp(0f, 360f, lightAngleOverTime.Evaluate(t));
            directionalLight.transform.rotation = Quaternion.Euler(angle, 30f, 0f);
        }

        RenderSettings.ambientLight = performanceMode ? Color.gray : ambientLightColor.Evaluate(t);
    }

    void ApplyFog(float t)
    {
        Color fogColor = Color.Lerp(fogColorNight, fogColorDay, Mathf.Sin(t * Mathf.PI));
        float fogDensity = Mathf.Lerp(fogDensityNight, fogDensityDay, Mathf.Sin(t * Mathf.PI));

        RenderSettings.fogColor = fogColor;
        RenderSettings.fogDensity = fogDensity;
    }

    [ContextMenu("⛔ Disable All Effects")]
    public void DisableAllEnvironment()
    {
        enableFog = false;
        autoCycle = false;
        RenderSettings.fog = false;

        if (directionalLight != null)
        {
            directionalLight.color = Color.white;
            directionalLight.intensity = 1f;
            directionalLight.transform.rotation = Quaternion.Euler(50f, 30f, 0f);
        }

        RenderSettings.ambientLight = Color.gray;
        Debug.Log("[EnvironmentManager] 모든 환경 효과 비활성화됨");
    }
}
