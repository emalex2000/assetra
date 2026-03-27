from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified
from rest_framework.response import Response
from .serializers import AssetSerializer, AssetCategorySerializer

class CreateAssetView(APIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        user = request.user
        if not user.company:
            return Response({"error":"you must belong to a company to create assets"}, status=403)
        serializer = AssetSerializer(data=request.data)
        if serializer.is_valid():
            asset = serializer.save(
                company=user.company
            )
            return Response({
                "message":"asset created successfully",
                "asset":AssetSerializer(asset).data
                }, status=201)
        return Response(serializer.errors, status=400)
    

class CreateCategoryView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]
    def post(self, request):
        user = request.user
        if not user.company:
            return Response({"error":"you must belong to a company first"}, status=403)
        serializers = AssetCategorySerializer(data=request.data)
        if serializers.is_valid():
            category = serializers.save(
                company = user.company
            )
            return Response({
                "message":"category created succesfully",
                "category" : AssetCategorySerializer(category).data
                }, status=201)
        return Response(serializers.errors, status=201)