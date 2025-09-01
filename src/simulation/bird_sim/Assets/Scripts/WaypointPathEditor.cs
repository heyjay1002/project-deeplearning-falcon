using UnityEngine;
using UnityEditor;

[CustomEditor(typeof(WaypointBezierPath))]
public class WaypointPathEditor : Editor
{
    private bool showAdvancedOptions = false;

    public override void OnInspectorGUI()
    {
        WaypointBezierPath path = (WaypointBezierPath)target;

        // 기본 인스펙터 그리기
        DrawDefaultInspector();

        EditorGUILayout.Space(10);
        EditorGUILayout.LabelField("웨이포인트 도구", EditorStyles.boldLabel);

        // 경로 상태 정보 표시
        DrawPathInfo(path);

        EditorGUILayout.Space(5);

        // 기본 버튼들 배치
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Add Waypoint"))
        {
            AddWaypoint(path);
        }
        
        if (GUILayout.Button("Insert Waypoint"))
        {
            InsertWaypoint(path);
        }
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Straighten Path"))
        {
            StraightenPath(path);
        }
        
        if (GUILayout.Button("Reverse Path"))
        {
            ReversePath(path);
        }
        EditorGUILayout.EndHorizontal();

        // 고급 옵션 토글 버튼
        showAdvancedOptions = EditorGUILayout.Foldout(showAdvancedOptions, "고급 옵션");
        
        if (showAdvancedOptions)
        {
            EditorGUI.indentLevel++;
            DrawAdvancedOptions(path);
            EditorGUI.indentLevel--;
        }

        // 경고 메시지와 도움말 표시
        DrawHelpBox(path);
    }

    // 경로 정보 표시
    private void DrawPathInfo(WaypointBezierPath path)
    {
        EditorGUILayout.BeginVertical(EditorStyles.helpBox);
        EditorGUILayout.LabelField("경로 정보", EditorStyles.boldLabel);
        
        string status = path.IsValid() ? "유효함" : "유효하지 않음";
        EditorGUILayout.LabelField($"상태: {status}");
        EditorGUILayout.LabelField($"웨이포인트: {path.waypoints.Count}개");
        
        if (path.IsValid())
        {
            float approximateLength = CalculateApproximateLength(path);
            EditorGUILayout.LabelField($"대략적인 길이: {approximateLength:F1} 단위");
        }
        
        EditorGUILayout.EndVertical();
    }

    // 고급 옵션 그리기
    private void DrawAdvancedOptions(WaypointBezierPath path)
    {
        EditorGUILayout.BeginVertical(EditorStyles.helpBox);
        
        if (GUILayout.Button("Optimize Waypoints"))
        {
            OptimizeWaypoints(path);
        }
        
        if (GUILayout.Button("Distribute Evenly"))
        {
            DistributeWaypointsEvenly(path);
        }
        
        if (GUILayout.Button("Clear All Waypoints"))
        {
            if (EditorUtility.DisplayDialog("확인", "모든 Waypoint를 삭제하시겠습니까?", "삭제", "취소"))
            {
                ClearWaypoints(path);
            }
        }
        
        EditorGUILayout.EndVertical();
    }

    // 도움말 및 경고 표시
    private void DrawHelpBox(WaypointBezierPath path)
    {
        if (!path.IsValid())
        {
            EditorGUILayout.HelpBox("경로가 유효하지 않습니다. 최소 2개의 웨이포인트가 필요합니다.", MessageType.Warning);
        }
        else if (path.waypoints.Count < 4)
        {
            EditorGUILayout.HelpBox("부드러운 곡선을 위해 4개 이상의 웨이포인트를 권장합니다.", MessageType.Info);
        }
    }

    // 웨이포인트를 경로 끝에 추가
    private void AddWaypoint(WaypointBezierPath path)
    {
        GameObject newWP = new GameObject($"Waypoint_{path.waypoints.Count}");
        newWP.transform.parent = path.transform;

        Vector3 basePos = path.waypoints.Count > 0
            ? path.waypoints[path.waypoints.Count - 1].position
            : path.transform.position;

        Vector3 offset = path.waypoints.Count > 1 
            ? (path.waypoints[path.waypoints.Count - 1].position - path.waypoints[path.waypoints.Count - 2].position)
            : Vector3.forward * 10f;

        newWP.transform.position = basePos + offset;

        Undo.RegisterCreatedObjectUndo(newWP, "Add Waypoint");
        path.waypoints.Add(newWP.transform);
        EditorUtility.SetDirty(path);
    }

    // 웨이포인트를 중간에 삽입
    private void InsertWaypoint(WaypointBezierPath path)
    {
        if (path.waypoints.Count < 2) return;

        int insertIndex = path.waypoints.Count / 2; // 중간에 삽입
        GameObject newWP = new GameObject($"Waypoint_{insertIndex}");
        newWP.transform.parent = path.transform;

        // 중간 지점 위치 계산
        Vector3 pos1 = path.waypoints[insertIndex - 1].position;
        Vector3 pos2 = path.waypoints[insertIndex].position;
        newWP.transform.position = Vector3.Lerp(pos1, pos2, 0.5f);

        Undo.RegisterCreatedObjectUndo(newWP, "Insert Waypoint");
        path.waypoints.Insert(insertIndex, newWP.transform);
        
        // 웨이포인트 이름 다시 정리
        UpdateWaypointNames(path);
        EditorUtility.SetDirty(path);
    }

    // 경로를 직선으로 만들기
    private void StraightenPath(WaypointBezierPath path)
    {
        if (path.waypoints.Count < 2) return;

        Undo.RecordObjects(path.waypoints.ToArray(), "Straighten Path");
        
        Vector3 start = path.waypoints[0].position;
        Vector3 end = path.waypoints[path.waypoints.Count - 1].position;
        
        for (int i = 1; i < path.waypoints.Count - 1; i++)
        {
            float t = (float)i / (path.waypoints.Count - 1);
            path.waypoints[i].position = Vector3.Lerp(start, end, t);
        }
        
        EditorUtility.SetDirty(path);
    }

    // 경로 순서 뒤집기
    private void ReversePath(WaypointBezierPath path)
    {
        if (path.waypoints.Count < 2) return;

        Undo.RecordObject(path, "Reverse Path");
        path.waypoints.Reverse();
        UpdateWaypointNames(path);
        EditorUtility.SetDirty(path);
    }

    // 웨이포인트 최적화 - 너무 가까운 점들 제거
    private void OptimizeWaypoints(WaypointBezierPath path)
    {
        if (path.waypoints.Count < 3) return;

        float minDistance = 1f; // 최소 거리 설정
        var toRemove = new System.Collections.Generic.List<Transform>();

        for (int i = 1; i < path.waypoints.Count - 1; i++)
        {
            float dist = Vector3.Distance(path.waypoints[i].position, path.waypoints[i - 1].position);
            if (dist < minDistance)
            {
                toRemove.Add(path.waypoints[i]);
            }
        }

        foreach (var wp in toRemove)
        {
            path.waypoints.Remove(wp);
            Undo.DestroyObjectImmediate(wp.gameObject);
        }

        UpdateWaypointNames(path);
        EditorUtility.SetDirty(path);
        Debug.Log($"최적화 완료: {toRemove.Count}개 웨이포인트 제거됨");
    }

    // 웨이포인트를 균등하게 분배
    private void DistributeWaypointsEvenly(WaypointBezierPath path)
    {
        if (path.waypoints.Count < 3) return;

        Undo.RecordObjects(path.waypoints.ToArray(), "Distribute Waypoints Evenly");
        
        Vector3 start = path.waypoints[0].position;
        Vector3 end = path.waypoints[path.waypoints.Count - 1].position;
        
        for (int i = 1; i < path.waypoints.Count - 1; i++)
        {
            float t = (float)i / (path.waypoints.Count - 1);
            path.waypoints[i].position = Vector3.Lerp(start, end, t);
        }
        
        EditorUtility.SetDirty(path);
    }

    // 모든 웨이포인트 삭제
    private void ClearWaypoints(WaypointBezierPath path)
    {
        foreach (var wp in path.waypoints)
        {
            if (wp != null)
                Undo.DestroyObjectImmediate(wp.gameObject);
        }

        path.waypoints.Clear();
        EditorUtility.SetDirty(path);
    }

    // 웨이포인트 이름 업데이트
    private void UpdateWaypointNames(WaypointBezierPath path)
    {
        for (int i = 0; i < path.waypoints.Count; i++)
        {
            if (path.waypoints[i] != null)
            {
                path.waypoints[i].gameObject.name = $"Waypoint_{i}";
            }
        }
    }

    // 경로 길이 근사 계산
    private float CalculateApproximateLength(WaypointBezierPath path)
    {
        if (!path.IsValid()) return 0f;

        float length = 0f;
        int samples = 50;
        Vector3 prev = path.GetPosition(0f);

        for (int i = 1; i <= samples; i++)
        {
            float t = (float)i / samples;
            Vector3 curr = path.GetPosition(t);
            length += Vector3.Distance(prev, curr);
            prev = curr;
        }

        return length;
    }
}
