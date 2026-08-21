package com.sktpj.gbmoder

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams

enum class LiveModeEntitlementState {
    CHECKING,
    FREE,
    ACTIVE,
    PENDING,
    ERROR,
}

object LiveModeBillingManager : PurchasesUpdatedListener {
    const val PRODUCT_ID = "live_mode"
    const val BASE_PLAN_ID = "monthly"

    private const val PAYWALL_NONE = 0
    private const val PAYWALL_PURCHASED = 1
    private const val PAYWALL_CANCELLED = 2

    private var appContext: Context? = null
    private var billingClient: BillingClient? = null
    private var connecting = false
    private var productDetails: ProductDetails? = null
    private var selectedOffer: ProductDetails.SubscriptionOfferDetails? = null

    @Volatile
    private var paywallResult: Int = PAYWALL_NONE

    var entitlementState by mutableStateOf(LiveModeEntitlementState.CHECKING)
        private set

    var formattedPrice by mutableStateOf<String?>(null)
        private set

    var canPurchase by mutableStateOf(false)
        private set

    @JvmStatic
    @Synchronized
    fun initialize(context: Context) {
        if (appContext == null) {
            appContext = context.applicationContext
        }
        if (billingClient == null) {
            val pendingParams = PendingPurchasesParams.newBuilder()
                .enableOneTimeProducts()
                .build()
            billingClient = BillingClient.newBuilder(context.applicationContext)
                .setListener(this)
                .enablePendingPurchases(pendingParams)
                .build()
        }
        connectIfNeeded()
    }

    @JvmStatic
    fun isEntitled(): Boolean = entitlementState == LiveModeEntitlementState.ACTIVE

    @JvmStatic
    fun refreshEntitlement() {
        val client = billingClient
        if (client == null) {
            appContext?.let(::initialize)
            return
        }
        if (!client.isReady) {
            connectIfNeeded()
            return
        }

        if (entitlementState != LiveModeEntitlementState.ACTIVE) {
            entitlementState = LiveModeEntitlementState.CHECKING
        }
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.SUBS)
            .build()
        client.queryPurchasesAsync(params) { billingResult, purchases ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                processPurchases(purchases)
            } else if (entitlementState != LiveModeEntitlementState.ACTIVE) {
                entitlementState = LiveModeEntitlementState.ERROR
            }
        }
    }

    fun launchPurchase(activity: Activity): Boolean {
        val client = billingClient
        val details = productDetails
        val offer = selectedOffer
        if (client == null || !client.isReady || details == null || offer == null) {
            initialize(activity)
            return false
        }

        val productParams = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(details)
            .setOfferToken(offer.offerToken)
            .build()
        val flowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(productParams))
            .build()
        val result = client.launchBillingFlow(activity, flowParams)
        if (result.responseCode == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
            refreshEntitlement()
        }
        return result.responseCode == BillingClient.BillingResponseCode.OK
    }

    fun openSubscriptionManagement(context: Context) {
        val uri = Uri.parse(
            "https://play.google.com/store/account/subscriptions?sku=$PRODUCT_ID&package=${context.packageName}",
        )
        val intent = Intent(Intent.ACTION_VIEW, uri)
        if (context !is Activity) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    @JvmStatic
    fun clearPaywallResult() {
        paywallResult = PAYWALL_NONE
    }

    @JvmStatic
    fun markPaywallPurchased() {
        paywallResult = PAYWALL_PURCHASED
    }

    @JvmStatic
    fun markPaywallCancelled() {
        paywallResult = PAYWALL_CANCELLED
    }

    @JvmStatic
    fun consumePaywallResult(): Int {
        val result = paywallResult
        paywallResult = PAYWALL_NONE
        return result
    }

    override fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> processPurchases(purchases.orEmpty())
            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> refreshEntitlement()
            BillingClient.BillingResponseCode.USER_CANCELED -> Unit
            else -> {
                if (entitlementState != LiveModeEntitlementState.ACTIVE) {
                    entitlementState = LiveModeEntitlementState.ERROR
                }
            }
        }
    }

    @Synchronized
    private fun connectIfNeeded() {
        val client = billingClient ?: return
        if (client.isReady) {
            queryProductDetails()
            refreshEntitlement()
            return
        }
        if (connecting) return
        connecting = true
        client.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                connecting = false
                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                    queryProductDetails()
                    refreshEntitlement()
                } else if (entitlementState != LiveModeEntitlementState.ACTIVE) {
                    entitlementState = LiveModeEntitlementState.ERROR
                }
            }

            override fun onBillingServiceDisconnected() {
                connecting = false
                canPurchase = false
            }
        })
    }

    private fun queryProductDetails() {
        val client = billingClient ?: return
        if (!client.isReady) return

        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(PRODUCT_ID)
            .setProductType(BillingClient.ProductType.SUBS)
            .build()
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(listOf(product))
            .build()

        client.queryProductDetailsAsync(params) { billingResult, queryResult ->
            if (billingResult.responseCode != BillingClient.BillingResponseCode.OK) {
                canPurchase = false
                return@queryProductDetailsAsync
            }

            val details = queryResult.productDetailsList.firstOrNull { it.productId == PRODUCT_ID }
            val offers = details?.subscriptionOfferDetails.orEmpty()
            val offer = offers.firstOrNull {
                it.basePlanId == BASE_PLAN_ID && it.offerId == null
            } ?: offers.firstOrNull { it.basePlanId == BASE_PLAN_ID }

            productDetails = details
            selectedOffer = offer
            formattedPrice = offer?.pricingPhases?.pricingPhaseList?.lastOrNull()?.formattedPrice
            canPurchase = details != null && offer != null
        }
    }

    private fun processPurchases(purchases: List<Purchase>) {
        val related = purchases.filter { purchase -> PRODUCT_ID in purchase.products }
        val purchased = related.firstOrNull {
            it.purchaseState == Purchase.PurchaseState.PURCHASED
        }
        if (purchased != null) {
            entitlementState = LiveModeEntitlementState.ACTIVE
            acknowledgeIfNeeded(purchased)
            return
        }

        val pending = related.any { it.purchaseState == Purchase.PurchaseState.PENDING }
        entitlementState = if (pending) {
            LiveModeEntitlementState.PENDING
        } else {
            LiveModeEntitlementState.FREE
        }
    }

    private fun acknowledgeIfNeeded(purchase: Purchase) {
        if (purchase.isAcknowledged) return
        val client = billingClient ?: return
        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        client.acknowledgePurchase(params) { billingResult ->
            if (billingResult.responseCode != BillingClient.BillingResponseCode.OK) {
                refreshEntitlement()
            }
        }
    }
}

@Composable
fun LiveModeSubscriptionCard() {
    val context = LocalContext.current
    val state = LiveModeBillingManager.entitlementState
    val price = LiveModeBillingManager.formattedPrice

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        stringResource(R.string.live_mode_title),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        when (state) {
                            LiveModeEntitlementState.ACTIVE -> stringResource(R.string.live_mode_status_active)
                            LiveModeEntitlementState.PENDING -> stringResource(R.string.live_mode_status_pending)
                            LiveModeEntitlementState.CHECKING -> stringResource(R.string.live_mode_status_loading)
                            else -> stringResource(R.string.live_mode_status_free)
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                if (state == LiveModeEntitlementState.ACTIVE) {
                    OutlinedButton(onClick = { LiveModeBillingManager.openSubscriptionManagement(context) }) {
                        Text(stringResource(R.string.live_mode_manage))
                    }
                }
            }
            Text(
                if (state == LiveModeEntitlementState.ACTIVE) {
                    stringResource(R.string.live_mode_active_description)
                } else {
                    stringResource(R.string.live_mode_paid_description, price ?: stringResource(R.string.live_mode_price_from_play))
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

class LiveModePaywallActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.enableEdgeToEdge(window)
        LiveModeBillingManager.clearPaywallResult()
        LiveModeBillingManager.initialize(this)
        setContent {
            GbModerTheme(this) {
                LiveModePaywallScreen(
                    activity = this,
                    onClose = ::cancelAndFinish,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        LiveModeBillingManager.refreshEntitlement()
    }

    private fun cancelAndFinish() {
        LiveModeBillingManager.markPaywallCancelled()
        setResult(Activity.RESULT_CANCELED)
        finish()
    }
}

@Composable
private fun LiveModePaywallScreen(
    activity: LiveModePaywallActivity,
    onClose: () -> Unit,
) {
    val state = LiveModeBillingManager.entitlementState
    val price = LiveModeBillingManager.formattedPrice
    val canPurchase = LiveModeBillingManager.canPurchase

    BackHandler(onBack = onClose)

    LaunchedEffect(state) {
        if (state == LiveModeEntitlementState.ACTIVE) {
            LiveModeBillingManager.markPaywallPurchased()
            activity.setResult(Activity.RESULT_OK)
            activity.finish()
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        contentWindowInsets = WindowInsets.safeDrawing,
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Spacer(Modifier.height(12.dp))

            Text(
                stringResource(R.string.live_mode_paywall_headline),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                stringResource(R.string.live_mode_paywall_body),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        stringResource(R.string.live_mode_benefit_realtime),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        stringResource(R.string.live_mode_other_free),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.primaryContainer,
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        price?.let { stringResource(R.string.live_mode_monthly_price, it) }
                            ?: stringResource(R.string.live_mode_price_loading),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        stringResource(R.string.live_mode_auto_renew),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            Text(
                stringResource(R.string.live_mode_cancel_info),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (state == LiveModeEntitlementState.PENDING) {
                Text(
                    stringResource(R.string.live_mode_pending_purchase),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            Button(
                onClick = { LiveModeBillingManager.launchPurchase(activity) },
                enabled = canPurchase && state != LiveModeEntitlementState.PENDING,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
            ) {
                Text(
                    if (canPurchase) {
                        stringResource(R.string.live_mode_subscribe)
                    } else {
                        stringResource(R.string.live_mode_loading_purchase)
                    },
                )
            }

            OutlinedButton(
                onClick = onClose,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.live_mode_not_now))
            }

            if (!canPurchase && state != LiveModeEntitlementState.CHECKING) {
                Text(
                    stringResource(R.string.live_mode_purchase_unavailable),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }

            Spacer(Modifier.height(12.dp))
        }
    }
}
