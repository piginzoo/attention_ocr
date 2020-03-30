# 之前报错：AttributeError: 'Bidirectional' object has no attribute 'outbound_nodes'
# from keras.layers import Bidirectional,Input, GRU, Dense, Concatenate, TimeDistributed,Reshape
# from tensorflow.python.keras.applications.vgg19 import VGG19
# from keras.applications.vgg19 import VGG19
# 原因是不能用keras自带的vgg19+keras自带的bidirectional，靠，肯定是版本不兼容的问题
# 切换到下面的就好了，之前还是试验了用tf的bidirectional+keras的vgg19，也是不行，报错：AttributeError: 'Node' object has no attribute 'output_masks'
# 靠谱的组合是：tf的bidirectional+tf的vgg19
from keras.layers import Bidirectional,Input, GRU, Dense, Concatenate, TimeDistributed
import tensorflow as tf
from keras.models import Model
from keras.optimizers import Adam
from keras.layers import Bidirectional,Input, GRU, Dense, Concatenate, TimeDistributed
from layers.conv import Conv
from layers.attention_layer import AttentionDecoder
import logging
from utils.logger import _p_shape,_p
logger = logging.getLogger("Model")


def words_accuracy(y_true, y_pred):

    max_idx_p = tf.argmax(y_pred, axis=2)
    max_idx_l = tf.argmax(y_true, axis=2)
    correct_pred = tf.equal(max_idx_p, max_idx_l)
    correct_pred = _p(correct_pred, "@@@,words_accuracy(字对字)")
    _result = tf.map_fn(fn=lambda e: tf.reduce_all(e), elems=correct_pred, dtype=tf.bool)
    _result = _p(_result, "@@@,words_accuracy(词对词)")
    result = tf.reduce_mean(tf.cast(_result, tf.float32))
    result = _p(result, "@@@,words_accuracy正确率")
    return result

# 焊接vgg和lstm，入参是vgg_conv5返回的张量
def model(conf,args):

    input_image = Input(shape=(conf.INPUT_IMAGE_HEIGHT,conf.INPUT_IMAGE_WIDTH,3), name='input_image') #高度固定为32，3通道

    conv = Conv().build(input_image)

    encoder_bi_gru = Bidirectional(GRU(conf.GRU_HIDDEN_SIZE,
                                       return_sequences=True,
                                       return_state=True,
                                       name='encoder_gru'),
                                   input_shape=(conf.INPUT_IMAGE_WIDTH/4,512),
                                   name='bidirectional_encoder')

    encoder_out, encoder_fwd_state, encoder_back_state = encoder_bi_gru(conv)

    logger.debug("双向输出encoder_out：\t%r",encoder_out.shape)
    logger.debug("双向输出encoder_fwd_state：\t%r", encoder_fwd_state.shape)
    logger.debug("双向输出encoder_back_state：\t%r", encoder_back_state.shape)

    decoder_inputs = Input(shape=(None,conf.CHARSET_SIZE), name='decoder_inputs')

    # decoder_gru = GRU(units=conf.GRU_HIDDEN_SIZE*2, return_sequences=True, return_state=True, name='decoder_gru')

    attn_layer = AttentionDecoder(units=conf.GRU_HIDDEN_SIZE,output_dim=conf.GRU_HIDDEN_SIZE)

    logger.debug("模型Attention调用的张量[encoder_out, decoder_out]:%r",encoder_out)
    attn_out = attn_layer(encoder_out) # c_outputs, e_outputs
    logger.debug("模型Attention输出的张量[attn_out]:%r", attn_out)

    train_model = Model(inputs=[input_image, decoder_inputs], outputs=[attn_out])
    opt = Adam(lr=args.learning_rate)

    train_model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=[words_accuracy])

    train_model.summary()

    return train_model